"use client";

import { useRef, useState } from "react";
import { Bot, Send, User } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ModuleIntro } from "@/components/modules/ModuleIntro";
import { Message, api } from "@/lib/api";

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Ask me about footprint hotspots, data quality, emission factor confidence, or supplier engagement priorities.",
    },
  ]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    const nextMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await api.chatAdvisor(
        text,
        nextMessages.filter((message) => message.role !== "assistant" || message.content !== messages[0].content),
        sessionId,
      );
      setSessionId(response.session_id);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.error ?? response.content,
        },
      ]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <ModuleIntro
        moduleKey="advisor"
        icon={Bot}
        title="Advisor"
        job="Ask questions about your footprints and the GHG Protocol."
        steps={[
          "Ask in plain language",
          "Grounded in your data plus the GHG Protocol",
          "Every answer cites its sources",
        ]}
        needs="At least one saved analysis, to ask about your own data (optional)."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="overflow-hidden">
        <CardHeader className="border-b bg-card">
          <CardTitle>Advisor chat</CardTitle>
          <CardDescription>{sessionId ? `Session ${sessionId}` : "New session"}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[58vh] min-h-[460px] space-y-5 overflow-y-auto bg-secondary/40 p-4 md:p-6">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              return (
                <div key={`${message.role}-${index}`} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser ? (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <Bot className="h-4 w-4" />
                    </div>
                  ) : null}
                  <div className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm shadow-xs ${isUser ? "bg-primary text-primary-foreground" : "bg-card"}`}>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                  {isUser ? (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
                      <User className="h-4 w-4" />
                    </div>
                  ) : null}
                </div>
              );
            })}
            {loading ? (
              <div className="flex gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl bg-card px-4 py-3 text-sm shadow-xs">
                  Thinking through your footprint data...
                </div>
              </div>
            ) : null}
          </div>
          <form ref={formRef} className="flex flex-col gap-3 border-t bg-card p-4 md:flex-row" onSubmit={sendMessage}>
            <Textarea
              className="min-h-[56px] md:min-h-[48px]"
              placeholder="Ask about hotspots, completeness, supplier priorities, or methodology..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  formRef.current?.requestSubmit();
                }
              }}
            />
            <Button className="md:h-auto" disabled={loading || !input.trim()} type="submit">
              <Send className="h-4 w-4" />
              Send
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
