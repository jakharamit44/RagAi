import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

with patch('qdrant_client.QdrantClient', return_value=MagicMock()):
    from api.scraper.crawler import UniversityWebCrawler

async def test_crawler_continuous_batching_auto_advancement():
    crawler = UniversityWebCrawler()

    seeds = ['https://mdu.ac.in/page1']
    allowed_domains = ['mdu.ac.in']
    batch_size = 5

    call_count = 0
    async def mock_process(client, job_id, url, depth, max_depth, allowed_domains, queue, visited, auto_ingest):
        nonlocal call_count
        call_count += 1
        crawler.stats['pages_scraped'] += 1
        if call_count == 1:
            for i in range(2, 13):
                link = f'https://mdu.ac.in/page{i}'
                visited.add(link)
                queue.append((link, 1))

    with patch.object(crawler, '_process_single_url', side_effect=mock_process), \
         patch('api.scraper.crawler.async_session_factory') as mock_session_factory:
        
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        await crawler._run_crawl_loop(
            job_id='test-job-id',
            seeds=seeds,
            allowed_domains=allowed_domains,
            max_depth=3,
            batch_size=batch_size,
            auto_ingest=False
        )

    assert crawler.stats['total_urls_visited'] == 12
    assert crawler.stats['current_batch'] == 3
    assert crawler.stats['batch_size'] == 5
    assert crawler.stats['queue_remaining'] == 0
    assert crawler.stats['pages_scraped'] == 12
    print('PASS: test_crawler_continuous_batching_auto_advancement')


async def test_crawler_stop_during_batching():
    crawler = UniversityWebCrawler()

    seeds = ['https://mdu.ac.in/seed']
    allowed_domains = ['mdu.ac.in']
    batch_size = 5

    call_count = 0
    async def mock_process(client, job_id, url, depth, max_depth, allowed_domains, queue, visited, auto_ingest):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            for i in range(2, 20):
                queue.append((f'https://mdu.ac.in/page{i}', 1))
        if call_count == 7:
            crawler.stop()

    with patch.object(crawler, '_process_single_url', side_effect=mock_process), \
         patch('api.scraper.crawler.async_session_factory') as mock_session_factory:

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        await crawler._run_crawl_loop(
            job_id='test-job-id',
            seeds=seeds,
            allowed_domains=allowed_domains,
            max_depth=3,
            batch_size=batch_size,
            auto_ingest=False
        )

    assert crawler.stop_requested is True
    assert crawler.stats['total_urls_visited'] == 7
    print('PASS: test_crawler_stop_during_batching')

if __name__ == '__main__':
    asyncio.run(test_crawler_continuous_batching_auto_advancement())
    asyncio.run(test_crawler_stop_during_batching())
    print('\nALL CRAWLER CONTINUOUS BATCHING TESTS PASSED!')
