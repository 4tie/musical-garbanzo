'use client';

import { useState } from 'react';
import Button from './Button';

interface CopyButtonProps {
  value: string;
  label?: string;
}

export default function CopyButton({ value, label = 'Copy' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <Button size="sm" variant="ghost" onClick={handleCopy}>
      {copied ? 'Copied' : label}
    </Button>
  );
}
