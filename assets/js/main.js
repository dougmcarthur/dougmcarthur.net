/* Shared site JS: newsletter signup via Pages Function -> Buttondown */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form.newsletter-form").forEach((form) => {
    const msg = form.querySelector(".form-msg");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = new FormData(form).get("email");
      msg.textContent = "Subscribing…";
      msg.className = "form-msg";
      try {
        const r = await fetch("/api/subscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        const data = await r.json().catch(() => ({}));
        if (r.ok) {
          msg.textContent = "You're in! Check your inbox to confirm.";
          msg.classList.add("ok");
          form.reset();
        } else {
          msg.textContent = data.error || "Something went wrong — try again.";
          msg.classList.add("err");
        }
      } catch {
        msg.textContent = "Network error — try again.";
        msg.classList.add("err");
      }
    });
  });
});


/* Contact form: explicit Turnstile render + POST to Pages Function -> Resend */
(function () {
  var TS_SITEKEY = "0x4AAAAAAFSm45W5SN0cvO6k";
  function renderTs() {
    var slot = document.getElementById("ts-contact");
    if (!slot || typeof turnstile === "undefined") return false;
    if (slot.dataset.rendered) return true;
    window.tsContactWidget = turnstile.render(slot, {
      sitekey: TS_SITEKEY,
      action: "contact",
    });
    slot.dataset.rendered = "1";
    return true;
  }
  function ensureTs(tries) {
    if (renderTs()) return;
    if (tries > 0) setTimeout(function () { ensureTs(tries - 1); }, 300);
  }
  function resetTs() {
    try {
      if (window.tsContactWidget !== undefined) turnstile.reset(window.tsContactWidget);
    } catch (_) {}
  }
  document.addEventListener("DOMContentLoaded", function () {
    ensureTs(20);
    document.querySelectorAll("form.contact-form").forEach(function (form) {
      var msg = form.querySelector(".form-msg");
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var fd = new FormData(form);
        var payload = {
          name: fd.get("name"),
          email: fd.get("email"),
          message: fd.get("message"),
          company: fd.get("company"),
          turnstile: fd.get("cf-turnstile-response"),
        };
        if (msg) {
          msg.textContent = "Sending…";
          msg.className = "form-msg";
        }
        try {
          var r = await fetch("/api/contact", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          var data = await r.json().catch(function () { return {}; });
          if (r.ok && msg) {
            msg.textContent = "Message sent — thanks!";
            msg.classList.add("ok");
            form.reset();
          } else if (msg) {
            msg.textContent = data.error || "Something went wrong — try again.";
            msg.classList.add("err");
          }
        } catch (_) {
          if (msg) {
            msg.textContent = "Network error — try again.";
            msg.classList.add("err");
          }
        }
        resetTs(); // tokens are single-use; reset for any retry
      });
    });
  });
})();

/* Mobile nav toggle */
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.querySelector(".nav-toggle");
  const nav = document.getElementById("main-nav");
  if (!btn || !nav) return;
  btn.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
});

/* Scroll reveals: fade/slide in as elements enter the viewport */
document.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("js");
  if (!("IntersectionObserver" in window)) return;
  const io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add("visible");
          io.unobserve(e.target);
        }
      }
    },
    { threshold: 0.1, rootMargin: "0px 0px -6% 0px" }
  );
  document
    .querySelectorAll(".card, .news-item, .newsletter, .embed")
    .forEach((el) => {
      el.classList.add("reveal");
      io.observe(el);
    });
});
