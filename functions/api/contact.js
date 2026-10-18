/**
 * POST /api/contact  { name, email, message, company?, turnstile? }
 * Contact form handler — no third-party form service. Sends via Resend.
 * Spam protection: Cloudflare Turnstile (human verification).
 * Setup:
 *  1. Free Resend account at resend.com, verify dougmcarthur.net (DNS TXT
 *     records), create an API key.
 *  2. Cloudflare dashboard > Turnstile > Add widget (free) for
 *     dougmcarthur.net — put the site key in content/pages/contact.md
 *     (data-sitekey) and the secret key in env vars.
 *  3. On the Cloudflare Pages project (Settings > Environment variables),
 *     set RESEND_API_KEY, TURNSTILE_SECRET_KEY
 *     (and optionally CONTACT_TO to override doug@dougmcarthur.net).
 */
export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }
  // Honeypot: bots fill this, humans don't (field is hidden)
  if (body.company) {
    return Response.json({ ok: true });
  }
  // Turnstile human verification (canonical siteverify)
  const tsSecret = context.env.TURNSTILE_SECRET_KEY;
  const tsToken = body.turnstile || "";
  if (
    !tsSecret ||
    typeof tsToken !== "string" ||
    tsToken.length === 0 ||
    tsToken.length > 2048
  ) {
    return Response.json(
      { error: "Please complete the human verification." },
      { status: 403 }
    );
  }
  let tsData;
  try {
    const tsRes = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ secret: tsSecret, response: tsToken }),
      }
    );
    tsData = await tsRes.json();
  } catch {
    return Response.json(
      { error: "Human verification failed — please try again." },
      { status: 403 }
    );
  }
  const allowedHosts = (context.env.TURNSTILE_HOSTNAMES || "")
    .split(",")
    .map((h) => h.trim())
    .filter(Boolean);
  if (
    !tsData.success ||
    tsData.action !== "contact" ||
    (allowedHosts.length > 0 && !allowedHosts.includes(tsData.hostname))
  ) {
    return Response.json(
      { error: "Human verification failed — please try again." },
      { status: 403 }
    );
  }
  const name = (body.name || "").trim().slice(0, 100);
  const email = (body.email || "").trim().slice(0, 200);
  const message = (body.message || "").trim().slice(0, 5000);
  if (!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || !message) {
    return Response.json(
      { error: "Please fill in your name, a valid email, and a message." },
      { status: 400 }
    );
  }
  const apiKey = context.env.RESEND_API_KEY;
  if (!apiKey) {
    return Response.json(
      { error: "Contact form isn't configured yet." },
      { status: 500 }
    );
  }
  const to = context.env.CONTACT_TO || "doug@dougmcarthur.net";
  // Show the sender's name in the From display name so it's visible in the
  // inbox. The address stays noreply@ (verified domain); replies go to the
  // sender via reply_to. Sanitize the name against header injection.
  const safeName = name.replace(/["<>\r\n]/g, "").trim().slice(0, 60) || "Website visitor";
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: `${safeName} (dougmcarthur.net) <noreply@dougmcarthur.net>`,
      to: [to],
      reply_to: `${safeName} <${email}>`,
      subject: `Website contact from ${safeName}`,
      text: `From: ${name} <${email}>\n\n${message}`,
    }),
  });
  if (res.ok) {
    return Response.json({ ok: true });
  }
  return Response.json(
    { error: "Message failed to send — please try again later." },
    { status: 502 }
  );
}
