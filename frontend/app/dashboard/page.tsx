"use client";

import { useEffect, useState } from "react";
import axios from "axios";

const backend = process.env.NEXT_PUBLIC_BACKEND_URL!;

type Email = {
  id: string;
  subject: string;
  from: string;
  snippet: string;
  body: string;
  summary?: string;
};

type ChatMessage = {
  id: string;
  from: "user" | "assistant";
  text: string;
};

function shorten(text: string, max = 140) {
  if (!text) return "";
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > max ? t.slice(0, max) + "..." : t;
}

function cleanSummary(summary: string | undefined, snippet: string) {
  if (!summary && !snippet) return "";
  let base = summary || snippet || "";
  base = base.replace(
    "AI summary unavailable (quota or model error). Preview:",
    "Preview:"
  );
  return shorten(base, 140);
}

export default function Dashboard() {
  const [userName, setUserName] = useState<string | null>(null);
  const [userPic, setUserPic] = useState<string | null>(null);
  const [emails, setEmails] = useState<Email[]>([]);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [pendingDeleteIndex, setPendingDeleteIndex] = useState<number | null>(
    null
  );
  const [pendingReplyIndex, setPendingReplyIndex] = useState<number | null>(
    null
  );
  const [generatedReplies, setGeneratedReplies] = useState<
    Record<string, string>
  >({});

  useEffect(() => {
    axios
      .get(`${backend}/auth/me`, { withCredentials: true })
      .then((res) => {
        setUserName(res.data.name || res.data.email);
        setUserPic(res.data.picture || null);
        setChat([
          {
            id: crypto.randomUUID(),
            from: "assistant",
            text:
              `Hi ${res.data.name || ""}! 👋 I’m your AI email assistant.\n\n` +
              "You can ask me things like:\n" +
              "• Show my last 5 emails\n" +
              "• Generate reply for email 2\n" +
              "• Send reply for email 2\n" +
              "• Delete email 3",
          },
        ]);
      })
      .catch(() => {
        window.location.href = "/";
      });
  }, []);

  const pushMessage = (m: ChatMessage) =>
    setChat((prev) => [...prev, m]);

  const handleShowLast5 = async () => {
    setLoadingEmails(true);
    pushMessage({
      id: crypto.randomUUID(),
      from: "user",
      text: "Show my last 5 emails",
    });

    try {
      const res = await axios.get(`${backend}/gmail/last5`, {
        withCredentials: true,
      });
      const msgs: Email[] = res.data.messages || [];
      setEmails(msgs);

      if (!msgs.length) {
        pushMessage({
          id: crypto.randomUUID(),
          from: "assistant",
          text: "I couldn't find any recent emails in your inbox.",
        });
        return;
      }

      const formatted = msgs
        .map((m, idx) => {
          const summary = cleanSummary(m.summary, m.snippet);
          return (
            `${idx + 1}) ${shorten(m.subject || "(no subject)", 70)}\n` +
            `   From: ${shorten(m.from || "", 70)}\n` +
            (summary ? `   Summary: ${summary}` : "")
          );
        })
        .join("\n\n");

      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text: "Here are your latest 5 emails:\n\n" + formatted,
      });
    } catch (err) {
      console.error(err);
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text:
          "I couldn't fetch your emails. Your session might have expired – try logging in again.",
      });
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleGenerateReply = async (index: number) => {
    const email = emails[index];
    if (!email) return;

    pushMessage({
      id: crypto.randomUUID(),
      from: "user",
      text: `Generate a reply for email ${index + 1}`,
    });

    try {
      const res = await axios.post(
        `${backend}/gmail/generate-reply/${email.id}`,
        {},
        { withCredentials: true }
      );
      const reply = res.data.reply as string;
      setGeneratedReplies((prev) => ({ ...prev, [email.id]: reply }));
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text:
          `Here's a suggested reply for email ${index + 1}:\n\n` +
          `${reply}\n\n` +
          `You can send it by saying "send reply for email ${index + 1}".`,
      });
      setPendingReplyIndex(index);
    } catch (err: any) {
      console.error(err);
      const msg =
        err?.response?.status === 429
          ? "AI reply generation is temporarily unavailable (quota or model error)."
          : "I couldn't generate a reply for that email.";
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text: msg,
      });
    }
  };

  const handleSendReply = async (index: number) => {
    const email = emails[index];
    if (!email) return;
    const reply = generatedReplies[email.id];
    if (!reply) {
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text:
          "I don't have a generated reply for that email yet. Ask me to generate one first.",
      });
      return;
    }

    pushMessage({
      id: crypto.randomUUID(),
      from: "user",
      text: `Send the reply for email ${index + 1}`,
    });

    try {
      const res = await axios.post(
        `${backend}/gmail/send-reply/${email.id}`,
        { reply_text: reply },
        { withCredentials: true }
      );
      if (res.data.status === "sent") {
        pushMessage({
          id: crypto.randomUUID(),
          from: "assistant",
          text: `✅ Reply for email ${index + 1} has been sent via Gmail.`,
        });
      } else {
        throw new Error("send failed");
      }
    } catch (err) {
      console.error(err);
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text: `I couldn't send the reply for email ${index + 1}.`,
      });
    }
  };

  const handleDeleteEmail = (index: number) => {
    const email = emails[index];
    if (!email) return;
    setPendingDeleteIndex(index);
    pushMessage({
      id: crypto.randomUUID(),
      from: "assistant",
      text: `Are you sure you want to delete email ${index + 1} (subject: "${shorten(
        email.subject,
        60
      )}")? Type "yes" to confirm or "no" to cancel.`,
    });
  };

  const confirmDelete = async () => {
    if (pendingDeleteIndex === null) return;
    const email = emails[pendingDeleteIndex];
    if (!email) return;

    try {
      const res = await axios.delete(
        `${backend}/gmail/delete/${email.id}`,
        { withCredentials: true }
      );
      if (res.data.status === "deleted") {
        pushMessage({
          id: crypto.randomUUID(),
          from: "assistant",
          text: `🗑️ Email ${pendingDeleteIndex + 1} has been deleted from your inbox.`,
        });
        setEmails((prev) =>
          prev.filter((_, idx) => idx !== pendingDeleteIndex)
        );
      } else {
        throw new Error("delete failed");
      }
    } catch (err) {
      console.error(err);
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text: "I couldn't delete that email.",
      });
    } finally {
      setPendingDeleteIndex(null);
    }
  };

  const cancelDelete = () => {
    setPendingDeleteIndex(null);
    pushMessage({
      id: crypto.randomUUID(),
      from: "assistant",
      text: "Okay, I won't delete that email.",
    });
  };

  const handleUserInput = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    const msg: ChatMessage = {
      id: crypto.randomUUID(),
      from: "user",
      text: trimmed,
    };
    pushMessage(msg);
    setInput("");

    const lower = trimmed.toLowerCase();

    if (pendingDeleteIndex !== null) {
      if (["yes", "y", "confirm"].includes(lower)) {
        await confirmDelete();
        return;
      }
      if (["no", "n", "cancel"].includes(lower)) {
        cancelDelete();
        return;
      }
      pushMessage({
        id: crypto.randomUUID(),
        from: "assistant",
        text: `Please answer "yes" or "no" for the delete confirmation.`,
      });
      return;
    }

    if (lower.includes("last 5") || lower.includes("last five")) {
      await handleShowLast5();
      return;
    }

    if (lower.startsWith("generate reply for email")) {
      const num = parseInt(lower.replace(/\D/g, ""), 10);
      if (!isNaN(num) && num >= 1 && num <= emails.length) {
        await handleGenerateReply(num - 1);
        return;
      }
    }

    if (lower.startsWith("send reply for email")) {
      const num = parseInt(lower.replace(/\D/g, ""), 10);
      if (!isNaN(num) && num >= 1 && num <= emails.length) {
        await handleSendReply(num - 1);
        return;
      }
    }

    if (lower.startsWith("delete email")) {
      const num = parseInt(lower.replace(/\D/g, ""), 10);
      if (!isNaN(num) && num >= 1 && num <= emails.length) {
        handleDeleteEmail(num - 1);
        return;
      }
    }

    pushMessage({
      id: crypto.randomUUID(),
      from: "assistant",
      text:
        "I didn't quite get that. You can ask me things like:\n" +
        "• Show my last 5 emails\n" +
        "• Generate reply for email 2\n" +
        "• Send reply for email 2\n" +
        "• Delete email 3",
    });
  };

  const handleLogout = () => {
    window.location.href = `${backend}/auth/logout`;
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center py-6">
      <div className="w-full max-w-6xl h-[80vh] bg-slate-900/80 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex">
        {/* LEFT: inbox cards */}
        <section className="w-2/5 border-right border-slate-800 flex flex-col">
          <header className="px-6 py-4 flex items-center justify-between bg-gradient-to-r from-indigo-500/20 via-slate-900 to-slate-900 border-r border-slate-800">
            <div className="flex items-center gap-3">
              {userPic ? (
                <img
                  src={userPic}
                  alt="avatar"
                  className="h-9 w-9 rounded-full border border-slate-700"
                />
              ) : (
                <div className="h-9 w-9 rounded-full bg-indigo-500 flex items-center justify-center font-semibold text-sm">
                  {(userName || "U")[0].toUpperCase()}
                </div>
              )}
              <div>
                <p className="text-xs text-slate-400">Logged in as</p>
                <p className="font-medium text-sm">{userName || "..."}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-full border border-slate-600 hover:bg-slate-800"
            >
              Logout
            </button>
          </header>

          <div className="px-4 py-3 flex items-center justify-between gap-3 border-r border-slate-800">
            <h2 className="text-sm font-semibold text-slate-300">
              Inbox overview
            </h2>
            <button
              onClick={handleShowLast5}
              disabled={loadingEmails}
              className="text-xs px-3 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60"
            >
              {loadingEmails ? "Loading..." : "Refresh last 5"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-3 border-r border-slate-800">
            {emails.length === 0 && !loadingEmails && (
              <p className="text-xs text-slate-500">
                Ask me to &quot;Show my last 5 emails&quot; to populate this
                list.
              </p>
            )}

            {emails.map((mail, idx) => {
              const summary = cleanSummary(mail.summary, mail.snippet);
              return (
                <div
                  key={mail.id}
                  className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-xs space-y-1"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-slate-500">
                      #{idx + 1}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleGenerateReply(idx)}
                        className="px-2 py-1 rounded-full bg-slate-800 hover:bg-slate-700"
                      >
                        ✨ Reply
                      </button>
                      <button
                        onClick={() => handleDeleteEmail(idx)}
                        className="px-2 py-1 rounded-full bg-slate-900 border border-red-500/50 text-red-300 hover:bg-red-500/10"
                      >
                        🗑 Delete
                      </button>
                    </div>
                  </div>
                  <p className="font-semibold text-slate-100 text-xs truncate">
                    {mail.subject || "(no subject)"}
                  </p>
                  <p className="text-[11px] text-slate-400 truncate">
                    {mail.from}
                  </p>
                  {summary && (
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {summary}
                    </p>
                  )}
                  {generatedReplies[mail.id] && (
                    <p className="mt-2 text-[11px] text-slate-300 bg-slate-800/80 rounded-xl p-2">
                      AI reply ready. Click{" "}
                      <button
                        onClick={() => handleSendReply(idx)}
                        className="underline font-medium"
                      >
                        send
                      </button>{" "}
                      or type &quot;send reply for email {idx + 1}&quot;.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* RIGHT: chat */}
        <section className="flex-1 flex flex-col">
          <header className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
            <div>
              <h1 className="text-sm font-semibold">Chatbot</h1>
              <p className="text-xs text-slate-400">
                Natural language control for your inbox.
              </p>
            </div>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full">
              ● Connected
            </span>
          </header>

          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 text-sm">
            {chat.map((m) => (
              <div
                key={m.id}
                className={`flex ${
                  m.from === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-3 py-2 whitespace-pre-wrap leading-relaxed ${
                    m.from === "user"
                      ? "bg-indigo-500 text-white rounded-br-sm"
                      : "bg-slate-800 text-slate-100 rounded-bl-sm"
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
          </div>

          <form
            className="p-4 border-t border-slate-800 flex gap-3 bg-slate-900/80"
            onSubmit={(e) => {
              e.preventDefault();
              handleUserInput();
            }}
          >
            <input
              className="flex-1 rounded-2xl bg-slate-800 border border-slate-700 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder='Try: "Show my last 5 emails" or "Delete email 2"'
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button
              type="submit"
              className="px-4 py-2 rounded-2xl bg-indigo-500 hover:bg-indigo-600 text-sm font-medium"
            >
              Send
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
