export default async function handler(req, res) {
  const source = String(req.query.url || "");
  if (!source) return res.status(400).json({ error: "missing url" });
  try {
    const apiUrl = "https://ahm7xmakki.com/api/alldl?url=" + encodeURIComponent(source);
    const r = await fetch(apiUrl, { headers: { "user-agent": "Mozilla/5.0" } });
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { return res.status(502).json({ error: "bad upstream", status: r.status, text: text.slice(0,1000) }); }
    if (!r.ok || data?.success === false) return res.status(502).json({ error: "upstream failed", status: r.status, data });
    const m = data?.mediaInfo || data?.data || data;
    const candidates = [
      ...(Array.isArray(m?.qualities) ? m.qualities.map(x => ({ url:x?.url || x?.videoUrl, quality:x?.quality || x?.label || "" })) : []),
      { url:m?.videoUrl, quality:"default" },
      { url:data?.videoUrl, quality:"default" }
    ].filter(x => typeof x.url === "string" && x.url.startsWith("http"));
    if (!candidates.length) return res.status(502).json({ error:"no video url", data });
    const pick = candidates.find(x => /720|1080|hd/i.test(String(x.quality))) || candidates[0];
    if (req.query.json === "1") return res.status(200).json({ picked:pick, candidates, title:m?.title || data?.title || null });
    res.setHeader("Location", pick.url);
    return res.status(302).end();
  } catch (e) {
    return res.status(500).json({ error:String(e?.message || e) });
  }
}