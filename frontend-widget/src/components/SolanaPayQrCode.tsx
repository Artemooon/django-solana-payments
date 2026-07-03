import { useEffect, useRef } from "react";
import { createQR } from "@solana/pay";

type SolanaPayQrCodeProps = {
  solanaPayUrl: string;
  size?: number;
};

export function SolanaPayQrCode({
  solanaPayUrl,
  size = 256,
}: SolanaPayQrCodeProps) {
  const qrRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = qrRef.current;
    if (!element) {
      return;
    }

    element.innerHTML = "";
    createQR(solanaPayUrl, size).append(element);

    return () => {
      element.innerHTML = "";
    };
  }, [solanaPayUrl, size]);

  return <div className="spw-qr" ref={qrRef} />;
}
