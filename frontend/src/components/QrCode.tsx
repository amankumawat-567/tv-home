import { useEffect, useRef } from "preact/hooks";
import QRCode from "qrcode";

export function QrCode({ value, size = 220 }: { value: string; size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, value, { width: size, margin: 1, color: { dark: "#101418", light: "#f1f3f5" } }).catch(() => undefined);
  }, [value, size]);

  return <canvas ref={canvasRef} width={size} height={size} className="qr-code" />;
}
