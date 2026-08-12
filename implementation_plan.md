# Terabox and Transcoding Timeline Solutions

## Open Questions & User Review Required

> [!WARNING]
> **Terabox Reality Check:** 
> Terabox actively uses Cloudflare to block all free scraping APIs. There is **no Python library in existence** that can reliably bypass Terabox without account credentials (cookies). If a tool claims to do it, it will break within days. 
> *Question:* Do you want me to integrate a cookie-based Terabox downloader (where you provide your `ndus` cookie), or should we drop Terabox support?

> [!IMPORTANT]
> **Why the Timeline/Seeking is Broken:**
> When you click "Fix Sound", the server uses FFmpeg to transcode the audio *on-the-fly* and pipes it directly to your browser as a live stream. Because it's a live stream, the browser doesn't know the total file size or duration, so it disables the timeline and seeking.

### Proposed Solutions for Video Seeking

I can implement one (or both) of the following solutions. Please tell me which you prefer:

**Option 1: HLS (Apple HTTP Live Streaming) Engine**
I can build a custom HLS transcoding engine. When you click "Fix Sound", it will convert the video into small `.ts` chunks in real-time. 
- *Pros:* You get a timeline, and it streams instantly.
- *Cons:* You can only seek backwards, or forwards up to the point FFmpeg has finished processing. You can't instantly skip to the end of the movie.

**Option 2: "Permanent Convert" Button**
I can add a button that runs a background FFmpeg task to permanently convert the `.mkv` / AC3 file into a perfectly compatible `.mp4` file on your storage drive.
- *Pros:* Perfect native playback on Safari/Chrome, 100% full seeking, and perfect timeline.
- *Cons:* You have to wait for the conversion to finish before watching (could take a few minutes on a phone).

**Option 3: Use the VLC Button (Recommended)**
You already have an "Open in VLC" button! VLC natively supports all complex audio formats and `.mkv` files. 
- *Pros:* Zero wait time, perfect seeking, no server CPU usage.

Please reply with how you want to proceed regarding Terabox and which Video Seeking option you prefer!
