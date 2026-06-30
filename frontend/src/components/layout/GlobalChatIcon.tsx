"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { ChatDrawer } from "@/components/layout/ChatDrawer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function GlobalChatIcon() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        size="icon"
        aria-label="Open AI assistant"
        className={cn(
          "fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full shadow-lg",
        )}
        onClick={() => setOpen(true)}
      >
        <Sparkles className="h-5 w-5" />
      </Button>
      <ChatDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}
