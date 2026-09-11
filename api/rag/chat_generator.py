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
    # Deduplicate repetitive phrase loops
    text = re.sub(r"(\b[\w\u0900-\u097F]{2,}\b(?:\s+[\w\u0900-\u097F]{2,}\b){0,4})(?:\s+\1){2,}", r"\1", text)
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
                        loaded = False
                        if getattr(settings, "ENABLE_4BIT_QUANTIZATION", True):
                            try:
                                from transformers import BitsAndBytesConfig
                                bnb_config = BitsAndBytesConfig(
                                    load_in_4bit=True,
                                    bnb_4bit_quant_type="nf4",
                                    bnb_4bit_use_double_quant=True,
                                    bnb_4bit_compute_dtype=torch.float16,
                                )
                                self._model = AutoModelForCausalLM.from_pretrained(
                                    target_dir,
                                    quantization_config=bnb_config,
                                    device_map="cuda",
                                    attn_implementation="sdpa",
                                    local_files_only=True,
                                )
                                loaded = True
                                logger.info("LocalChatGenerator: 4-bit NF4 quantization enabled (VRAM ~1.85 GB).")
                            except Exception as bnb_err:
                                logger.warning(f"4-bit quantization fallback ({bnb_err}). Loading in FP16...")

                        if not loaded:
                            try:
                                self._model = AutoModelForCausalLM.from_pretrained(
                                    target_dir,
                                    torch_dtype=torch.float16,
                                    device_map="cuda",
                                    attn_implementation="sdpa",
                                    local_files_only=True,
                                )
                                logger.info("LocalChatGenerator: Hardware-accelerated SDPA attention enabled (FP16).")
                            except Exception as sdpa_err:
                                logger.info(f"SDPA not enabled ({sdpa_err}), falling back to standard attention (FP16).")
                                self._model = AutoModelForCausalLM.from_pretrained(
                                    target_dir,
                                    torch_dtype=torch.float16,
                                    device_map="cuda",
                                    local_files_only=True,
                                )
                    else:
                        self._model = AutoModelForCausalLM.from_pretrained(
                            target_dir,
                            torch_dtype=torch.float32,
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
        inputs = None
        outputs = None
        generated_ids = None
        import gc
        try:
            with gpu_lock:
                inputs = tokenizer([prompt_text], return_tensors="pt").to(model.device)
                is_sampling = temperature > 0.05
                generation_kwargs = dict(
                    **inputs,
                    max_new_tokens=effective_tokens,
                    temperature=temperature if is_sampling else None,
                    do_sample=is_sampling,
                    top_p=0.9 if is_sampling else None,
                    repetition_penalty=1.1,
                    use_cache=True,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
                with torch.inference_mode():
                    if torch.cuda.is_available():
                        with torch.amp.autocast("cuda", dtype=torch.float16):
                            outputs = model.generate(**generation_kwargs)
                    else:
                        outputs = model.generate(**generation_kwargs)
                # Slice off input tokens to get newly generated response
                generated_ids = outputs[0][len(inputs.input_ids[0]):].detach().cpu()
                if torch.cuda.is_available():
                    torch.cuda.synchronize()

            response_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
            return response_text
        except Exception as gen_err:
            if "out of memory" in str(gen_err).lower():
                logger.error("CUDA OOM detected during generation, releasing memory cache...")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            raise gen_err
        finally:
            if 'inputs' in locals():
                del inputs
            if 'outputs' in locals():
                del outputs
            if 'generated_ids' in locals():
                del generated_ids

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

        from .self_improver import PromptRuleManager
        dynamic_rules = PromptRuleManager.get_rules()
        rules_text = "\n".join([f"{idx+1}. {r.replace('{cur_date_str}', cur_date_str)}" for idx, r in enumerate(dynamic_rules)])

        system_instruction = (
            "You are the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            f"CURRENT REAL-TIME DATE & TIME: {cur_date_str} at {cur_time_str} (Academic Session: {cur_year}-{cur_year+1}).\n\n"
            "Your role is to assist students, researchers, and faculty by providing helpful, polite, and accurate information "
            "strictly grounded in verified university documents, course syllabi, and official minutes.\n\n"
            f"RULES:\n{rules_text}"
        )

        from api.core.conversational import is_hindi_or_hinglish
        if is_hindi_or_hinglish(question):
            lang_instruction = "\n\nCRITICAL LANGUAGE INSTRUCTION: The student asked in Hindi or Hinglish. Answer in polite, natural Hindi or Hinglish matching the student's language."
        else:
            lang_instruction = "\n\nCRITICAL LANGUAGE INSTRUCTION: The student asked in English. Answer in clear, polite English."

        user_content = (
            f"<untrusted_academic_context>\n{context_block}\n</untrusted_academic_context>\n\n"
            f"Question: {question}{lang_instruction}\n\nAnswer:"
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

        import threading
        from transformers import StoppingCriteria, StoppingCriteriaList

        stop_event = threading.Event()

        class StreamCancellationCriteria(StoppingCriteria):
            def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
                return stop_event.is_set()

        async_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _generate_worker():
            inputs = None
            try:
                from api.core.gpu_lock import gpu_lock
                with gpu_lock:
                    inputs = tokenizer([prompt_text], return_tensors="pt").to(model.device)
                    is_sampling = temperature > 0.05
                    generation_kwargs = dict(
                        **inputs,
                        streamer=streamer,
                        max_new_tokens=effective_tokens,
                        temperature=temperature if is_sampling else None,
                        do_sample=is_sampling,
                        top_p=0.9 if is_sampling else None,
                        repetition_penalty=1.1,
                        use_cache=True,
                        stopping_criteria=StoppingCriteriaList([StreamCancellationCriteria()]),
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
                if "out of memory" in str(e).lower() and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                loop.call_soon_threadsafe(async_queue.put_nowait, e)
            finally:
                if inputs is not None:
                    del inputs

        def _feeder_worker():
            try:
                for chunk in streamer:
                    if stop_event.is_set():
                        break
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
            stop_event.set()
            gen_thread.join(timeout=1.5)
            feed_thread.join(timeout=1.5)

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

        from .self_improver import PromptRuleManager
        dynamic_rules = PromptRuleManager.get_rules()
        rules_text = "\n".join([f"{idx+1}. {r.replace('{cur_date_str}', cur_date_str)}" for idx, r in enumerate(dynamic_rules)])

        system_instruction = (
            "You are the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak.\n"
            f"CURRENT REAL-TIME DATE & TIME: {cur_date_str} at {cur_time_str} (Academic Session: {cur_year}-{cur_year+1}).\n\n"
            "Your role is to assist students, researchers, and faculty by providing helpful, polite, and accurate information "
            "strictly grounded in verified university documents, course syllabi, and official minutes.\n\n"
            f"RULES:\n{rules_text}"
        )

        from api.core.conversational import is_hindi_or_hinglish
        if is_hindi_or_hinglish(question):
            lang_instruction = "\n\nCRITICAL LANGUAGE INSTRUCTION: The student asked in Hindi or Hinglish. Answer in polite, natural Hindi or Hinglish matching the student's language."
        else:
            lang_instruction = "\n\nCRITICAL LANGUAGE INSTRUCTION: The student asked in English. Answer in clear, polite English."

        user_content = (
            f"<untrusted_academic_context>\n{context_block}\n</untrusted_academic_context>\n\n"
            f"Question: {question}{lang_instruction}\n\nAnswer:"
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

