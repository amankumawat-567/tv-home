// "Logo centred on the app's brand colour (taken from the icon's edge pixels)" —
// sample a ring of pixels around the icon's border and average them. Falls back
// to a stable hash-based colour when there's no icon yet or the image can't be
// read (e.g. still loading on the real PC's slower disk).
const cache = new Map<string, string>();

function hashColor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return `hsl(${hue} 55% 28%)`;
}

export async function brandColorFor(id: string, iconUrl: string | null): Promise<string> {
  const cached = cache.get(id);
  if (cached) return cached;
  if (!iconUrl) {
    const color = hashColor(id);
    cache.set(id, color);
    return color;
  }
  try {
    const color = await sampleEdgeColor(iconUrl);
    cache.set(id, color);
    return color;
  } catch {
    const color = hashColor(id);
    cache.set(id, color);
    return color;
  }
}

function sampleEdgeColor(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const size = 32;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("no 2d context");
        ctx.drawImage(img, 0, 0, size, size);
        const { data } = ctx.getImageData(0, 0, size, size);
        let r = 0,
          g = 0,
          b = 0,
          n = 0;
        for (let x = 0; x < size; x++) {
          for (const y of [0, size - 1]) addPixel(data, x, y, size);
        }
        for (let y = 0; y < size; y++) {
          for (const x of [0, size - 1]) addPixel(data, x, y, size);
        }
        function addPixel(d: Uint8ClampedArray, x: number, y: number, s: number) {
          const i = (y * s + x) * 4;
          if (d[i + 3] < 10) return; // skip transparent edge pixels
          r += d[i];
          g += d[i + 1];
          b += d[i + 2];
          n++;
        }
        if (n === 0) throw new Error("fully transparent icon");
        resolve(`rgb(${Math.round(r / n)} ${Math.round(g / n)} ${Math.round(b / n)})`);
      } catch (err) {
        reject(err as Error);
      }
    };
    img.onerror = () => reject(new Error("icon failed to load"));
    img.src = url;
  });
}
