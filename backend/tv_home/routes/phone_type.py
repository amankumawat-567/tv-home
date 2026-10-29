from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .. import info, phone_type

router = APIRouter()


class TypeValueBody(BaseModel):
    value: str


@router.post("/api/type/start")
async def start_typing():
    token = phone_type.start()
    ip = info.ip_address()
    host = ip or "127.0.0.1"
    return {"token": token, "url": f"http://{host}:8000/type/{token}"}


@router.get("/api/type/{token}")
async def get_typing(token: str):
    session = phone_type.get(token)
    if session is None:
        raise HTTPException(404, "That session has expired.")
    return session


@router.post("/api/type/{token}/end")
async def end_typing(token: str):
    phone_type.end(token)
    return {"ok": True}


@router.post("/type/{token}")
async def phone_post_value(token: str, body: TypeValueBody):
    if not phone_type.set_value(token, body.value):
        raise HTTPException(404, "That session has expired.")
    return {"ok": True}


@router.post("/type/{token}/done")
async def phone_post_done(token: str):
    if not phone_type.mark_done(token):
        raise HTTPException(404, "That session has expired.")
    return {"ok": True}


@router.get("/type/{token}", response_class=HTMLResponse)
async def phone_type_page(token: str):
    session = phone_type.get(token)
    if session is None:
        return HTMLResponse("<p>This code has expired — go back to the TV and open the keyboard again.</p>", status_code=404)
    return HTMLResponse(_PAGE.replace("__TOKEN__", token))


# A standalone page — deliberately not part of the main frontend bundle, since
# it's opened on the phone, not the TV. Posts on every keystroke (debounced)
# so the TV-side poll (OnScreenKeyboard.tsx) stays current without the phone
# needing its own "send" step; "Done" ends the session and tells the TV to
# submit immediately rather than waiting for its own Done/OK.
_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>TV Home — Type</title>
<style>
  body { margin: 0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
         background: #101418; color: #f1f3f5; font-family: -apple-system, system-ui, sans-serif; padding: 24px; box-sizing: border-box; }
  textarea { width: 100%; max-width: 480px; min-height: 120px; font-size: 20px; padding: 12px; border-radius: 8px;
             border: 1px solid #262c36; background: #1b2028; color: #f1f3f5; box-sizing: border-box; }
  button { margin-top: 16px; padding: 14px 28px; font-size: 18px; border-radius: 24px; border: none; background: #ffb547;
           color: #101418; font-weight: 600; width: 100%; max-width: 480px; }
  p { color: #a9b1bc; }
  #status { font-size: 14px; }
</style>
</head>
<body>
  <p>Type below — it appears on the TV as you go.</p>
  <textarea id="box" autofocus placeholder="Start typing…"></textarea>
  <button id="done">Done</button>
  <p id="status"></p>
<script>
  const token = "__TOKEN__";
  const box = document.getElementById("box");
  const status = document.getElementById("status");
  let timer = null;
  box.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(send, 250);
  });
  async function send() {
    try {
      await fetch("/type/" + token, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value: box.value }) });
      status.textContent = "";
    } catch (e) {
      status.textContent = "Couldn't reach the TV — check you're on the same Wi-Fi.";
    }
  }
  document.getElementById("done").addEventListener("click", async () => {
    await send();
    await fetch("/type/" + token + "/done", { method: "POST" });
    status.textContent = "Sent — check the TV.";
    document.getElementById("done").disabled = true;
  });
</script>
</body>
</html>"""
