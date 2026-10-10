// GitHub OAuth gateway for Decap CMS.
// Expects GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET as Pages env vars.
// Flow: /api/auth -> redirect to GitHub -> GitHub redirects back with ?code=
// -> exchange code for token -> postMessage token to Decap popup opener.

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const clientId = env.GITHUB_CLIENT_ID;

  if (!clientId) {
    return new Response("GitHub OAuth not configured", { status: 500 });
  }

  // Step 1: no code yet — send the user to GitHub to authorize.
  if (!code) {
    const redirectUri = `${url.origin}/api/auth`;
    const authUrl =
      "https://github.com/login/oauth/authorize" +
      `?client_id=${encodeURIComponent(clientId)}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      "&scope=repo";
    return Response.redirect(authUrl, 302);
  }

  // Step 2: GitHub sent us back with a code — exchange it for a token.
  if (!env.GITHUB_CLIENT_SECRET) {
    return new Response("GitHub OAuth not configured", { status: 500 });
  }
  let tokenData;
  try {
    const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: env.GITHUB_CLIENT_SECRET,
        code,
      }),
    });
    tokenData = await tokenRes.json();
  } catch {
    return new Response("Token exchange failed", { status: 502 });
  }

  const token = tokenData && tokenData.access_token;
  const payload = token
    ? { token, provider: "github" }
    : { error: (tokenData && tokenData.error_description) || "OAuth failed" };

  // Step 3: hand the result back to the Decap CMS popup opener.
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${
    token ? "Authorized" : "Authorization failed"
  }</title></head><body><script>
    (function () {
      var message = ${JSON.stringify(
        "authorization:github:" + (token ? "success:" : "error:") + JSON.stringify(payload)
      )};
      if (window.opener) {
        window.opener.postMessage(message, "*");
      }
      document.body.textContent = ${JSON.stringify(
        token ? "Authorized — you can close this window." : "Authorization failed: " + (payload.error || "")
      )};
      if (window.opener) { try { window.close(); } catch (e) {} }
    })();
  </script></body></html>`;

  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
