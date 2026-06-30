"use client";

import { useRef, useState } from "react";
import { Send } from "lucide-react";

import { ModuleButtons } from "@/components/chat/ModuleButtons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  showModuleButtons?: boolean;
}

export function ChatInput({
  onSend,
  disabled = false,
  showModuleButtons = true,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || disabled) return;
    onSend(text);
    setInput("");
  }

  return (
    <div className="flex flex-col gap-3 border-t bg-white p-4">
      <form
        ref={formRef}
        className="flex flex-col gap-3 md:flex-row"
        onSubmit={handleSubmit}
      >
        <Textarea
          className="min-h-[56px] md:min-h-[48px]"
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
