import math
import random
import re
import urllib.parse
from js import window  # type: ignore
from pyodide.http import pyfetch  # type: ignore
from pyscript import document  # type: ignore
SLANG_MAP = {
    r"\bvery\b": "hella",
    r"\bgood\b": "fire",
    r"\bgreat\b": "goated",
    r"\bbad\b": "mid",
    r"\btrue\b": "no cap",
    r"\breally\b": "fr",
    r"\bpeople\b": "folks",
    r"\bmoney\b": "bands",
    r"\bfriend\b": "homie",
    r"\bfriends\b": "the squad",
    r"\bfamous\b": "lowkey iconic",
    r"\bborn\b": "spawned",
    r"\bdied\b": "took an L",
    r"\bis\b": "be",
    r"\bwas\b": "used to be",
    r"\blarge\b": "massive",
    r"\bsmall\b": "lil",
    r"\bimportant\b": "clutch",
    r"\bstudy\b": "grind",
    r"\btheory\b": "lore",
    r"\bbrain\b": "noggin",
    r"\bexample\b": "receipt",
    r"\bhowever\b": "lowkey though",
    r"\btherefore\b": "so basically",
}

INTROS = [
    "Yo, peep the lore:",
    "Bet, here's the tea:",
    "Say less, fam:",
    "Lowkey, check this out:",
]

OUTROS = [
    "That's on periodt. 💅",
    "No cap. 💯",
    "Easy W. 🔥",
    "Stay woke on that. 🧠",
]


def slangify(text):
  for word, slang in SLANG_MAP.items():
    text = re.sub(word, slang, text, flags=re.IGNORECASE)
  return f"{random.choice(INTROS)} {text} {random.choice(OUTROS)}"


def add_message(sender, text, css_class, tag="", img_url=""):
  chat_box = document.getElementById("chat-box")
  tag_html = f'<span class="tag">{tag}</span>' if tag else ""
  img_html = f'<img src="{img_url}" class="preview-img">' if img_url else ""
  chat_box.innerHTML += (
      f'<div class="msg">{tag_html}<span class="{css_class}">{sender}:</span>'
      f" {text}{img_html}</div>"
  )
  chat_box.scrollTop = chat_box.scrollHeight


def try_solve_math(query):
  cleaned = re.sub(
      r"(what is|whats|calculate|solve|evaluate|find|math|\?|=)",
      "",
      query,
      flags=re.IGNORECASE,
  ).strip()
  cleaned = cleaned.replace("^", "**").replace("×", "*").replace("÷", "/")
  cleaned = re.sub(r"(\d)\s*x\s*(\d)", r"\1*\2", cleaned, flags=re.IGNORECASE)

  if re.match(r"^[0-9\+\-\*\/\(\)\.\s\%a-zA-Z]+$", cleaned) and any(
      c.isdigit() for c in cleaned
  ):
    try:
      safe_env = {
          k: v for k, v in math.__dict__.items() if not k.startswith("__")
      }
      result = eval(cleaned, {"__builtins__": None}, safe_env)
      return round(result, 6) if isinstance(result, float) else result
    except Exception:
      return None
  return None


def clean_question(query):
  fillers = [
      (
          r"^(can you\s+|could you\s+|please\s+)?(explain|define|tell me"
          r" about|describe|summarize|help me with|what is|what are|who is|who"
          r" was|where is|when did|why does|why did|how does|how do)\s+"
      ),
      r"^(the\s+|a\s+|an\s+)",
      r"\b(in simple terms|for school|for ap|definition|meaning)\b",
  ]
  cleaned = query.strip("?.! \n\t")
  for f in fillers:
    cleaned = re.sub(f, "", cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


async def search_wikipedia(topic):
  if not topic:
    return None, None
  encoded_query = urllib.parse.quote(topic[:150])
  search_url = f"https://wikipedia.org{encoded_query}&limit=1&namespace=0&format=json&origin=*"

  search_res = await pyfetch(search_url)
  if search_res.status != 200:
    return None, None

  search_data = await search_res.json()
  if not search_data:
    return None, None

  best_title = search_data
  summary_url = f"https://wikipedia.org{urllib.parse.quote(best_title.replace(' ', '_'))}"
  summary_res = await pyfetch(summary_url)
  if summary_res.status == 200:
    data = await summary_res.json()
    return best_title, data.get("extract", "")
  return None, None


async def ask_bot(event=None):
  input_el = document.getElementById("topicInput")
  user_text = input_el.value.strip()
  file_text = window.attachedFileText.strip()
  img_url = window.attachedImageURL
  file_name = window.attachedFileName

  if not user_text and not file_text and not img_url:
    return

  display_msg = user_text if user_text else f"<i>[Uploaded {file_name}]</i>"
  add_message("You", display_msg, "user", img_url=img_url)

  input_el.value = ""
  window.clearFile()

  combined_query = f"{user_text} {file_text}".strip()

  for candidate in [user_text, file_text, combined_query]:
    if candidate:
      math_ans = try_solve_math(candidate)
      if math_ans is not None:
        add_message(
            "AI",
            f"Quick maths: that equals <b>{math_ans}</b>. Easy W. 🧮",
            "bot",
            tag="Math",
        )
        return

  if file_text:
    short_ocr = (file_text[:120] + "...") if len(file_text) > 120 else file_text
    add_message(
        "AI",
        f'Peeped your file/screenshot and read: <i>"{short_ocr}"</i>',
        "bot",
        tag="File Scan",
    )

  search_target = (
      clean_question(user_text) if user_text else clean_question(file_text)
  )

  if file_text and (not user_text or len(search_target) < 3):
    lines = [
        line.strip() for line in file_text.splitlines() if len(line.strip()) > 3
    ]
    if lines:
      search_target = clean_question(lines)

  try:
    title, extract = await search_wikipedia(search_target)
    if extract:
      sentences = extract.split(". ")[:3]
      short_summary = ". ".join(sentences)
      if not short_summary.endswith("."):
        short_summary += "."

      reply = slangify(short_summary)
      add_message("AI", reply, "bot", tag=title)
    else:
      add_message(
          "AI",
          (
              f"Bruh, I scanned '{search_target}' across the whole wiki and"
              " came up empty. Try highlighting the main keyword or formula fr."
          ),
          "bot",
          tag="No Match",
      )
  except Exception:
    add_message(
        "AI",
        "Oof, my connection glitched trying to look that up. Try again in a"
        " sec!",
        "bot",
    )


async def handle_enter(event):
  if event.key == "Enter":
    await ask_bot()
