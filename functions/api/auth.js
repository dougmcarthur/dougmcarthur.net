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

  // Step 3: hand the result back to the Decap CMS popup opener.
  // Decap's client requires a handshake: the popup must first post
  // "authorizing:github", then Decap echoes it back, and only then does the
  // popup deliver the "authorization:github:success:..." payload.
  const resultMessage = token
    ? "authorization:github:success:" + JSON.stringify({ token, provider: "github" })
    : "authorization:github:error:" + JSON.stringify({
        message: (tokenData && tokenData.error_description) || "OAuth failed",
      });
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${
    token ? "Authorized" : "Authorization failed"
  }</title></head><body><script>
    (function () {
      var resultMessage = ${JSON.stringify(resultMessage)};
      var doneMessage = ${JSON.stringify(
        token ? "Authorized — you can close this window." : "Authorization failed."
      )};
      function receiveMessage(e) {
        window.removeEventListener("message", receiveMessage, false);
        // Decap echoed our handshake; deliver the result to its origin.
        if (window.opener) {
          window.opener.postMessage(resultMessage, e.origin);
        }
        document.body.textContent = doneMessage;
        try { window.close(); } catch (err) {}
      }
      window.addEventListener("message", receiveMessage, false);
      // Start the handshake with the Decap CMS parent window.
      if (window.opener) {
        window.opener.postMessage("authorizing:github", "*");
      }
    })();
  </script></body></html>`;

  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
