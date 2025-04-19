import ahocorasick
import html

def search_brotli_dict_words(brotli_dict, text, output):
    automaton = ahocorasick.Automaton()
    with open(brotli_dict, "r", encoding="utf-8") as f:
        for idx, word in enumerate(f):
            word = word.strip()[1:-1] # Remove surrounding quotes
            word = word.replace(r'\"', '"')  # Unescape \" to "
            automaton.add_word(word, (idx, word))
    automaton.make_automaton()

    with open(text, "r", encoding="utf-8") as f:
        text = f.read()

    annotations = {}
    for idx, char in enumerate(text):
        # letter_html = "&nbsp;" if " " else
        annotations[idx] = {
            "letter": char,
            "letter_html": html.escape(char),
            "words": set()
        }

    for end_idx, (_, word) in automaton.iter(text):
        l = len(word)
        start_idx = end_idx - l + 1
        for i in range(l):
            idx = start_idx + i
            annotations[idx]["words"].add(word)

    html_list = "["

    annotated_html = []
    for idx, a in enumerate(annotations):
        obj = annotations[a]
        c = obj["letter_html"]
        words = list(obj["words"])
        html_list += "["
        if words:
            words.sort(reverse=True, key=lambda x: len(x))
            words = list(map(lambda w: "'" + w + "'", words))
            html_list += ",".join(words)
            # for w in words:
            #     if ">" in w: raise Exception(f"Fail: {w}")
            # w = "<br />".join(words)
            c = f"<div class='h' data-tooltip='{str(idx)}'>{c}</div>"
        else:
            c = f"<div class='n'>{c}</div>"

        html_list += "],"
        annotated_html.append(c)

    html_list += "];"

    html_content = f"""<!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Brotli dictionary highlighted</title>
        <style>
            body {{
                font-family: monospace, Consolar, DejaVu Sans Mono, Lucida Console, Courier, 'Courier New';
                font-size: 20px;
                line-height: 2;
                color: #c9c9c9;
                background-color: #121212;
            }}
            .cont {{
                width: 1200px;
                display: flex;
                flex-wrap: wrap;
                padding: 60px 30px;
            }}
            .h {{
                color: #02c44f;
                position: relative;
            }}
            .h, .n {{
                white-space: pre;
            }}
            #tooltip {{
                position: absolute;
                background-color: black;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                white-space: nowrap;
                display: none;
                transform: translate(-50%, -100%);
            }}
        </style>
    </head>
    <body>
        <div class='cont'>
            {"".join(annotated_html)}
        </div>
        <div id='tooltip'></div>
        <script>
            const annotations = {html_list}
            const tooltip = document.getElementById('tooltip');
            document.querySelectorAll('.h').forEach((el) => {{
                el.addEventListener('mouseenter', (event) => {{
                    let idx = event.target.getAttribute('data-tooltip') * 1;
                    let a = annotations[idx];
                    a = a.map(d => d.replace(/</g, "&lt;").replace(/>/g, "&gt;"));
                    tooltip.innerHTML = a.join("<br />");
                    tooltip.style.display = 'block';
                    const rect = event.target.getBoundingClientRect();
                    const scrollX = window.scrollX;
                    const scrollY = window.scrollY;
                    tooltip.style.left = `${{rect.left + rect.width / 2 + scrollX}}px`;
                    tooltip.style.top = `${{rect.top + scrollY - 10}}px`;
                }});
                el.addEventListener('mouseleave', () => {{
                    tooltip.style.display = 'none';
                }});
            }});
        </script>
    </body>
    </html>
    """
    with open(output, "w", encoding="utf-8") as f:
        f.write(html_content)

    # print("")
    # print(f"Highlighting complete. Open {output} to view.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("brotli_dict", help="Brotli dictionary")
    p.add_argument("text", help="Text file")
    p.add_argument("output", help="HTML file with words highlighted")
    args = p.parse_args()
    search_brotli_dict_words(args.brotli_dict, args.text, args.output)
