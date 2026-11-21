# TODO

## Done
- [x] Upload endpoint with extension + size checks, streamed to disk
- [x] Normalize every format to 16kHz mono wav with ffmpeg
- [x] faster-whisper transcription with VAD, mock backend for tests
- [x] Segment timestamps, json / srt / vtt / txt output
- [x] Async jobs: upload returns 202 + job_id, workers process in background
- [x] Job state in sqlite, unfinished jobs re-queued on restart
- [x] Retries with exponential backoff, no retry for bad audio
- [x] Manual retry endpoint for failed jobs
- [x] Long files split into chunks, timestamps shifted by chunk offset
- [x] Optional API key and webhook on completion
- [x] Tests

## Next
- [ ] Move queue to Redis/RQ or Celery so API and workers scale separately
- [ ] Store audio in S3 instead of local disk
- [ ] Save results per chunk so a retry resumes from the failed chunk
- [ ] Small overlap between chunks to avoid cutting words at boundaries
- [ ] Rate limiting per API key
- [ ] Sign webhook payloads (HMAC) and retry failed webhooks
- [ ] Cleanup job for old uploads and results
- [ ] Postprocessing: punctuation fixes, speaker diarization (pyannote)
- [ ] Sync endpoint for very short clips
- [ ] Dockerfile + docker-compose (api, worker, redis)
- [ ] Metrics: queue length, job latency, failure rate (Prometheus)
- [ ] GPU worker option (WHISPER_DEVICE=cuda, compute float16)
