"use client";

import { useRef, useState } from "react";
import { Plus, Send } from "lucide-react";

import { MODULE_BUTTONS, ModuleButtons } from "@/components/chat/ModuleButtons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  showModuleButtons?: boolean;
  /**
   * "docked" (default) is the bottom-pinned bar used once a conversation
   * has messages. "hero" is the same input styled as a standalone centered
   * card for the empty-thread welcome screen.
   */
  variant?: "hero" | "docked";
}

export function ChatInput({
  onSend,
  disabled = false,
  showModuleButtons = true,
  variant = "docked",
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  const isHero = variant === "hero";

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || disabled) return;
    onSend(text);
    setInput("");
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 bg-card p-4",
        isHero
          ? "rounded-2xl border shadow-xs md:p-5"
          : "border-t",
      )}
    >
      <form
        ref={formRef}
        className="flex flex-col gap-3 md:flex-row md:items-end"
        onSubmit={handleSubmit}
      >
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="shrink-0"
          disabled={disabled}
          aria-label="Attach a bill of materials"
          onClick={() => onSend(MODULE_BUTTONS[0].message)}
        >
          <Plus className="h-4 w-4" />
        </Button>
        <Textarea
          className={cn(isHero ? "min-h-[64px]" : "min-h-[56px] md:min-h-[48px]")}
          placeholder="Ask about footprints, hotspots, methodology, or supplier engagement..."
          value={input}
          disabled={disabled}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              formRef.current?.requestSubmit();
            }
          }}
        />
        <Button
          className="md:h-auto"
          disabled={disabled || !input.trim()}
          type="submit"
        >
          <Send className="h-4 w-4" />
          Send
        </Button>
      </form>
      {showModuleButtons ? (
        <ModuleButtons onSelect={onSend} disabled={disabled} />
      ) : null}
    </div>
  );
}
