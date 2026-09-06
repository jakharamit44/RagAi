import re
import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def clean_rag_answer(text: str) -> str:
    """Removes any accidental bracketed citations or pseudo-markdown links from model response."""
    if not text:
        return ""
    # Remove markdown/pseudo-markdown links like [Source 1](...) or [Document 1](...) including nested parentheses
    text = re.sub(r"\[(?:Source|Document|Ref)?\s*\d*\]\((?:[^()]|\([^()]*\))*\)", "", text, flags=re.IGNORECASE)
    # Remove file-link citations like [filename.pdf](...) or [filename.pdf]
    text = re.sub(r"\[[^\]]+\.(?:pdf|docx|txt|doc|json|pptx|xlsx)[^\]]*\](?:\((?:[^()]|\([^()]*\))*\))?", "", text, flags=re.IGNORECASE)
    # Remove parenthesized file references like (1st meeting...pdf, Page 1) or (Source 1, Page 1)
    text = re.sub(r"\((?:Source|Document)?\s*[^()]*\.(?:pdf|docx|txt|doc)[^()]*\)", "", text, flags=re.IGNORECASE)
    # Remove raw bracketed references like [Source 1], [Document 1], [Source: ...], [1], [2]
    text = re.sub(r"\[(?:Source|Document)[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\d+\]", "", text)
    # Remove dangling introductory/referential phrases
    text = re.sub(r"\b(?:as\s+(?:explicitly\s+)?stated\s+in|according\s+to|as\s+shown\s+in|as\s+referenced\s+in|as\s+per)\s*,\s*", "", text, flags=re.IGNORECASE)
    # Remove dangling prepositions before punctuation like "in ." -> "." or "according to ." -> "."
    text = re.sub(r"\s+\b(?:in|from|per|according\s+to|as\s+(?:explicitly\s+)?stated\s+in)\s*([.,;:!?])", r"\1", text, flags=re.IGNORECASE)
    # Remove trailing prepositions at end of string
    text = re.sub(r"\s+\b(?:in|from|per|according\s+to|as\s+(?:explicitly\s+)?stated\s+in)\s*$", ".", text, flags=re.IGNORECASE)
    # Clean multiple spaces and whitespace before punctuation
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text.strip()

class LocalChatGenerator:
    """
    Enterprise In-Project Local GPU Chat Generator.
    Executes Qwen2.5-3B-Instruct directly on NVIDIA CUDA GPU.
    Runs asynchronously in thread pools to handle concurrent student queries without freezing.
    Zero external daemon dependencies (no Ollama, no vLLM, no OpenAI).
    """

    def __init__(self, model_dir: Optional[str] = None):
        import threading
        self.model_dir = model_dir
        self._model = None
        self._tokenizer = None
        self._load_attempted = False
        self._gpu_async_lock: Optional[asyncio.Lock] = None
        self._load_lock = threading.Lock()

    @property
    def gpu_async_lock(self) -> asyncio.Lock:
        if self._gpu_async_lock is None:
            self._gpu_async_lock = asyncio.Lock()
        return self._gpu_async_lock

    def _get_model_and_tokenizer(self):
        with self._load_lock:
            if not self._load_attempted:
                self._load_attempted = True
                try:
                    import torch
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    from api.core.config import settings

                    target_dir = self.model_dir or settings.resolved_chat_model
                    device = "cuda" if torch.cuda.is_available() else "cpu"

                    logger.info(f"Loading local chat model from project folder: {target_dir} on {device}...")
                    t0 = time.time()
                    
                    self._tokenizer = AutoTokenizer.from_pretrained(target_dir, local_files_only=True)
                    
                    if device == "cuda":
                        try:
                            self._model = AutoModelForCausalLM.from_pretrained(
                                target_dir,
                                dtype=torch.float16,
                                device_map="cuda",
                                attn_implementation="sdpa",
                                local_files_only=True,
                            )
                            logger.info("LocalChatGenerator: Hardware-accelerated SDPA attention enabled.")
                        except Exception as sdpa_err:
                            logger.info(f"SDPA not enabled ({sdpa_err}), falling back to standard attention.")
                            self._model = AutoModelForCausalLM.from_pretrained(
                                target_dir,
                                dtype=torch.float16,
                                device_map="cuda",
                                local_files_only=True,
                            )
                    else:
                        self._model = AutoModelForCausalLM.from_pretrained(
                            target_dir,
                            dtype=torch.float32,
                            local_files_only=True,
                        ).to("cpu")

                    elapsed = time.time() - t0
                    vram_gb = (torch.cuda.memory_allocated(0) / (1024**3)) if device == "cuda" else 0.0
                    logger.info(f"Loaded local chat model in {elapsed:.2f}s! VRAM: {vram_gb:.2f} GB on {device}")
                except Exception as e:
                    logger.warning(f"LocalChatGenerator could not load model ({e}). Fallback to deterministic synthesis.")
                    self._model = None
                    self._tokenizer = None

        return self._model, self._tokenizer

    def warmup(self):
        """Pre-warms chat model during server startup so first student query is fast."""
        model, tokenizer = self._get_model_and_tokenizer()
        if model and tokenizer:
            try:
                messages = [
                    {"role": "system", "content": "You are a helpful university academic assistant."},
                    {"role": "user", "content": "Hello!"}
                ]
                text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer([text], return_tensors="pt").to(model.device)
                import torch
                with torch.inference_mode():
                    _ = model.generate(
                        **inputs,
                        max_new_tokens=10,
                        temperature=0.1,
                        use_cache=True,
                        pad_token_id=tokenizer.eos_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
                logger.info("LocalChatGenerator pre-warmed successfully on GPU.")
            except Exception as e:
                logger.warning(f"LocalChatGenerator warmup note: {e}")

    def is_available(self) -> bool:
        m, t = self._get_model_and_tokenizer()
        return (m is not None and t is not None)

    def _sync_generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ) -> str:
        """Synchronous PyTorch generation executed within worker thread with zero-overhead inference_mode."""
        model, tokenizer = self._get_model_and_tokenizer()
        if not model or not tokenizer:
            raise RuntimeError("Local chat model is not loaded.")

        from api.core.config import settings
        effective_tokens = max_new_tokens or getattr(settings, "MAX_NEW_TOKENS", 768)

        prompt_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        import torch
        from api.core.gpu_lock import gpu_lock
        try:
            with gpu_lock:
                inputs = tokenizer([prompt_text], return_tensors="pt").to(model.device)
                with torch.inference_mode():
                    if torch.cuda.is_available():
                        with torch.amp.autocast("cuda", dtype=torch.float16):
                            outputs = model.generate(
                                **inputs,
                                max_new_tokens=effective_tokens,
                                temperature=temperature if temperature > 0.0 else None,
                                do_sample=temperature > 0.0,
                                top_p=0.9 if temperature > 0.0 else None,
                                repetition_penalty=1.1,
                                use_cache=True,
                                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                                eos_token_id=tokenizer.eos_token_id,
                            )
                    else:
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=effective_tokens,
                            temperature=temperature if temperature > 0.0 else None,
                            do_sample=temperature > 0.0,
                            top_p=0.9 if temperature > 0.0 else None,
                            repetition_penalty=1.1,
                            use_cache=True,
                            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                            eos_token_id=tokenizer.eos_token_id,
                        )
                # Slice off input tokens to get newly generated response
                generated_ids = outputs[0][len(inputs.input_ids[0]):].detach().cpu()
                if torch.cuda.is_available():
                    torch.cuda.synchronize()

            response_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
            return response_text
        except Exception as gen_err:
            if "out of memory" in str(gen_err).lower():
                logger.error("CUDA OOM detected during generation, releasing memory cache...")
                torch.cuda.empty_cache()
            raise gen_err

    async def generate_rag_answer(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ) -> str:
        """
        Generates an accurate, grounded answer using verified academic context.
        Uses asyncio lock and thread pool to prevent GPU memory collisions under heavy load.
        """
        if not self.is_available():
            raise RuntimeError("Local chat model is not ready.")

        # Build clean, fenced academic context
        formatted_chunks = []
        for c in chunks:
            doc_title = c.get("title", "Verified Document")
            page_num = c.get("page_number", 1)
            snippet = c.get("text", "").strip()
            formatted_chunks.append(f"Document Reference: {doc_title} | Page: {page_num}\n{snippet}")

        context_block = "\n\n---\n\n".join(formatted_chunks)

        from datetime import datetime
        now = datetime.now()
        cur_date_str = now.strftime("%A, %B %d, %Y")
        cur_time_str = now.strftime("%I:%M %p")
        cur_year = now.year

        system_instruction = (
            "You are the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            f"CURRENT REAL-TIME DATE & TIME: {cur_date_str} at {cur_time_str} (Academic Session: {cur_year}-{cur_year+1}).\n\n"
            "Your role is to assist students, researchers, and faculty by providing helpful, polite, and accurate information "
            "strictly grounded in verified university documents, course syllabi, and official minutes.\n\n"
            "RULES:\n"
            "1. Base your factual academic answers ONLY on the verified context below. Do not hallucinate or invent facts.\n"
            f"2. TEMPORAL & RECENCY AWARENESS: Today's date is {cur_date_str}. Use this date to evaluate current academic status, upcoming vs past events, and whether deadlines have passed or been extended. When multiple notices exist, prioritize the latest extension notices, updated circulars, and current session guidelines.\n"
            "3. If the user greets you or includes conversational courtesies (like 'hi', 'hello', 'how are you'), respond warmly and politely as the MDU Rohtak AI Academic Assistant.\n"
            "4. If the user asks who you are or who developed you, clearly identify yourself as the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            "5. State key academic facts directly and clearly (dates, meeting numbers, course codes, exam schedules, rules).\n"
            "6. Do NOT include bracketed source tags, citation numbers, or markdown links like '[Source 1]', '[Source 1](...)', or '(Page X)' in your response text. Source citations and document badges are already displayed automatically by the user interface below your answer.\n"
            "7. If the context does not contain sufficient information to answer an academic question, state politely:\n"
            "'I do not have sufficient verified course material to answer this question. Please refer to your faculty or syllabus.'\n"
            "8. Never mention internal software development plans, requirements planning, document ingestion pipelines, administrative dashboards, or technical code to the user. You are an academic assistant communicating with university students.\n"
            "9. When asked about university admissions, summarize the verified guidelines, programs, submission deadlines, and official portal (www.mdu.ac.in) found in the documents.\n"
            "10. Provide a complete, fully formed answer. Always finish your thoughts, sentences, and lists cleanly without cutting off abruptly."
        )

        user_content = (
            f"<untrusted_academic_context>\n{context_block}\n</untrusted_academic_context>\n\n"
            f"Question: {question}\n\nAnswer:"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

        async with self.gpu_async_lock:
            raw_answer = await asyncio.to_thread(
                self._sync_generate,
                messages=messages,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            return clean_rag_answer(raw_answer)

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ) -> str:
        """OpenAI-compatible generic chat completion."""
        async with self.gpu_async_lock:
            return await asyncio.to_thread(
                self._sync_generate,
                messages=messages,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )

    async def _stream_generator_helper(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ):
        model, tokenizer = self._get_model_and_tokenizer()
        if not model or not tokenizer:
            raise RuntimeError("Local chat model is not loaded.")

        from transformers import TextIteratorStreamer
        from threading import Thread
        import torch
        from api.core.config import settings

        effective_tokens = max_new_tokens or getattr(settings, "MAX_NEW_TOKENS", 768)

        prompt_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=30.0,
        )

        async_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _generate_worker():
            try:
                from api.core.gpu_lock import gpu_lock
                with gpu_lock:
                    inputs = tokenizer([prompt_text], return_tensors="pt").to(model.device)
                    generation_kwargs = dict(
                        **inputs,
                        streamer=streamer,
                        max_new_tokens=effective_tokens,
                        temperature=temperature if temperature > 0.0 else None,
                        do_sample=temperature > 0.0,
                        top_p=0.9 if temperature > 0.0 else None,
                        repetition_penalty=1.1,
                        use_cache=True,
                        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
                    with torch.inference_mode():
                        if torch.cuda.is_available():
                            with torch.amp.autocast("cuda", dtype=torch.float16):
                                model.generate(**generation_kwargs)
                        else:
                            model.generate(**generation_kwargs)
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
            except Exception as e:
                loop.call_soon_threadsafe(async_queue.put_nowait, e)

        def _feeder_worker():
            try:
                for chunk in streamer:
                    loop.call_soon_threadsafe(async_queue.put_nowait, chunk)
                loop.call_soon_threadsafe(async_queue.put_nowait, None)
            except Exception as e:
                loop.call_soon_threadsafe(async_queue.put_nowait, e)

        gen_thread = Thread(target=_generate_worker)
        gen_thread.start()

        feed_thread = Thread(target=_feeder_worker)
        feed_thread.start()

        try:
            while True:
                token = await async_queue.get()
                if token is None:
                    break
                if isinstance(token, Exception):
                    raise token
                yield token
        finally:
            gen_thread.join(timeout=1.0)
            feed_thread.join(timeout=1.0)

    async def generate_rag_stream(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ):
        """Asynchronous SSE token streamer for verified academic question answering."""
        if not self.is_available():
            raise RuntimeError("Local chat model is not ready.")

        formatted_chunks = []
        for c in chunks:
            doc_title = c.get("title", "Verified Document")
            page_num = c.get("page_number", 1)
            snippet = c.get("text", "").strip()
            formatted_chunks.append(f"Document Reference: {doc_title} | Page: {page_num}\n{snippet}")

        context_block = "\n\n---\n\n".join(formatted_chunks)

        from datetime import datetime
        now = datetime.now()
        cur_date_str = now.strftime("%A, %B %d, %Y")
        cur_time_str = now.strftime("%I:%M %p")
        cur_year = now.year

        system_instruction = (
            "You are the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            f"CURRENT REAL-TIME DATE & TIME: {cur_date_str} at {cur_time_str} (Academic Session: {cur_year}-{cur_year+1}).\n\n"
            "Your role is to assist students, researchers, and faculty by providing helpful, polite, and accurate information "
            "strictly grounded in verified university documents, course syllabi, and official minutes.\n\n"
            "RULES:\n"
            "1. Base your factual academic answers ONLY on the verified context below. Do not hallucinate or invent facts.\n"
            f"2. TEMPORAL & RECENCY AWARENESS: Today's date is {cur_date_str}. Use this date to evaluate current academic status, upcoming vs past events, and whether deadlines have passed or been extended. When multiple notices exist, prioritize the latest extension notices, updated circulars, and current session guidelines.\n"
            "3. If the user greets you or includes conversational courtesies (like 'hi', 'hello', 'how are you'), respond warmly and politely as the MDU Rohtak AI Academic Assistant.\n"
            "4. If the user asks who you are or who developed you, clearly identify yourself as the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            "5. State key academic facts directly and clearly (dates, meeting numbers, course codes, exam schedules, rules).\n"
            "6. Do NOT include bracketed source tags, citation numbers, or markdown links like '[Source 1]', '[Source 1](...)', or '(Page X)' in your response text. Source citations and document badges are already displayed automatically by the user interface below your answer.\n"
            "7. If the context does not contain sufficient information to answer an academic question, state politely:\n"
            "'I do not have sufficient verified course material to answer this question. Please refer to your faculty or syllabus.'\n"
            "8. Never mention internal software development plans, requirements planning, document ingestion pipelines, administrative dashboards, or technical code to the user. You are an academic assistant communicating with university students.\n"
            "9. When asked about university admissions, summarize the verified guidelines, programs, submission deadlines, and official portal (www.mdu.ac.in) found in the documents.\n"
            "10. Provide a complete, fully formed answer. Always finish your thoughts, sentences, and lists cleanly without cutting off abruptly."
        )

        user_content = (
            f"<untrusted_academic_context>\n{context_block}\n</untrusted_academic_context>\n\n"
            f"Question: {question}\n\nAnswer:"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

        async with self.gpu_async_lock:
            async for token in self._stream_generator_helper(
                messages=messages,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            ):
                yield token

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_new_tokens: Optional[int] = None,
    ):
        """OpenAI-compatible asynchronous token streamer."""
        async with self.gpu_async_lock:
            async for token in self._stream_generator_helper(
                messages=messages,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            ):
                yield token

chat_generator = LocalChatGenerator()

