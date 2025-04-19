import brotli

# Brotli packing first introduced (I think?) by Muhmac / Speckdrumm in Felid: https://demozoo.org/graphics/342293/
# This is more optimized version with following improvements:
# * Use hardcoded file size
# * Inline URL assignment
# * Inline retriving file contents
# * Inline content length assignment
# * Use assignments return values
# * Use c alias for Command
# * Use Net.HttpListener instead of System.Net.HttpListener
# * Remove unnecessary spaces

# These lines are trimmed & line breaks removed. Spaces within strings remain and are neceeasry.
BOOTSTRAP_CODE = """
@powershell -c \"
&{
  ($h=[Net.HttpListener]::new()).Prefixes.Add(($u='http://localhost:9999/'));
  $h.Start();
  Start %1 $u;
  do{$c=$h.GetContext()}while($c.Request.RawUrl-ne'/');
  ($r=$c.Response).AddHeader('Content-Encoding','br');
  $r.OutputStream.Write((Get-Content '%~f0' -Encoding Byte -Raw),YYY,($r.ContentLength64=XXXX))
}
\"&exit/b
"""

BOOTSTRAP = ""
for s in BOOTSTRAP_CODE.split("\n"):
  s = s.strip()
  if s: BOOTSTRAP += s

# Add +1 for \n added to separate powershell script and brotli encoded content
OVERHEAD = len(BOOTSTRAP) + 1

def compress_html_file(html_content, slow):
  smallestSize = -1
  smallest = None
  lgblockRange = [0] if not slow else range(16, 25)
  lgwinRange = [22] if not slow else range(10, 25)

  html_content = html_content.replace("<html>", "<html>\n")
  encoded = html_content.encode("utf-8")
  for lgblock in lgblockRange:
    for lgwin in lgwinRange:
      compressed_content = brotli.compress(encoded, lgwin=lgwin, lgblock=lgblock)
      if not smallest or len(compressed_content) < smallestSize:
        smallest = compressed_content
        smallestSize = len(compressed_content)

  #  string (bytes): The input data.
  #  mode (int, optional): The compression mode can be MODE_GENERIC (default),
  #    MODE_TEXT (for UTF-8 format text input) or MODE_FONT (for WOFF 2.0).
  #  quality (int, optional): Controls the compression-speed vs compression-
  #    density tradeoff. The higher the quality, the slower the compression.
  #    Range is 0 to 11. Defaults to 11.
  #  lgwin (int, optional): Base 2 logarithm of the sliding window size. Range
  #    is 10 to 24. Defaults to 22.
  #  lgblock (int, optional): Base 2 logarithm of the maximum input block size.
  #    Range is 16 to 24. If set to 0, the value will be set based on the
  #    quality. Defaults to 0.
  return smallest


def bootstrap(brotli_content):
  boot = BOOTSTRAP
  boot = boot.replace("XXXX", str(len(brotli_content)))
  boot = boot.replace("YYY", str(OVERHEAD))
  return boot.encode("utf-8") + b"\n" + brotli_content


def get_bootstraped_size(compressed):
  return len(compressed) + OVERHEAD
