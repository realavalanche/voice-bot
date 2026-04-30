import asyncio, base64, wave, struct, httpx

def make_test_wav(duration_s=1, sample_rate=16000) -> bytes:
    """Generates a silent WAV — enough to test the pipeline shape."""
    num_samples = duration_s * sample_rate
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30) as c:
        # Health
        r = await c.get("/health")
        print("Health:", r.json()["status"])
        print("  ChromaDB — faq:", r.json()["chroma"]["faq_docs"],
              "products:", r.json()["chroma"]["product_docs"])

        # Text chat
        r = await c.post("/api/chat", json={
            "message": "What sizes do your formal shirts come in?",
            "language": "en-IN"
        })
        data = r.json()
        print("\nChat intent:", data["intent"])
        print("Response:", data["response"])

        # Voice (silent audio — transcript will be empty, tests pipeline)
        wav = make_test_wav()
        r = await c.post("/api/voice-chat",
                         files={"audio": ("test.wav", wav, "audio/wav")})
        print("\nVoice pipeline:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            print("  Transcript:", repr(data["transcript"]))
            print("  Intent:", data["intent"])
            print("  Time:", data["processing_time_ms"], "ms")
            print("  Audio bytes:", len(base64.b64decode(data["audio_base64"])))
        else:
            print("  Error:", r.json().get("detail", r.text))
            print("  (Use a real WAV recording to test voice end-to-end)")

asyncio.run(main())
