/**
 * POST /api/subscribe  { email }
 * Proxies newsletter signups to Buttondown so the API key never leaves the server.
 * Setup: create a free Buttondown account, then set the BUTTONDOWN_API_KEY
 * environment variable on the Cloudflare Pages project (Settings > Environment variables).
 */
export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }
  const email = (body.email || "").trim();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return Response.json({ error: "Please enter a valid email address." }, { status: 400 });
  }
  const apiKey = context.env.BUTTONDOWN_API_KEY;
  if (!apiKey) {
    return Response.json({ error: "Newsletter signup isn't configured yet." }, { status: 500 });
  }
  const res = await fetch("https://api.buttondown.com/v1/subscribers", {
    method: "POST",
    headers: {
      Authorization: `Token ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email_address: email, tags: ["website"] }),
  });
  if (res.status === 201) {
    return Response.json({ ok: true });
  }
  if (res.status === 400) {
    // Buttondown returns 400 for already-subscribed addresses
    const data = await res.json().catch(() => ({}));
    const detail = JSON.stringify(data).toLowerCase();
    if (detail.includes("already")) {
      return Response.json({ ok: true, note: "already subscribed" });
    }
    return Response.json({ error: "debug", bd_status: res.status, bd_body: data }, { status: 400 });
  }
  return Response.json({ error: "Signup failed — please try again later." }, { status: 502 });
}
