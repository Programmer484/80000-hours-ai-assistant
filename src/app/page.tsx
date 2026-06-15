'use client';

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';

type Citation = {
  citation_id: number;
  source_id: number;
  quote: string;
  matched_text: string;
  title: string;
  url: string;
};

type Message = {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
};

// Build a URL that scrolls to and highlights the exact cited text in the article
// using the Text Fragments spec (#:~:text=). We strip any fragment the backend
// already added so we don't end up with a broken double `#:~:text=`.
function buildCitationHref(cit: Citation): string {
  const base = cit.url.split('#')[0];
  const text = (cit.matched_text || cit.quote || '').trim();
  if (!text) return base;
  // Text fragments require -, &, and , to be percent-encoded within each text part.
  const enc = (s: string) => encodeURIComponent(s).replace(/-/g, '%2D');
  const words = text.split(/\s+/);
  // Long quotes can span block boundaries and fail to match, so anchor with
  // textStart,textEnd instead of the full string.
  const fragment =
    words.length > 12
      ? `${enc(words.slice(0, 5).join(' '))},${enc(words.slice(-5).join(' '))}`
      : enc(text);
  return `${base}#:~:text=${fragment}`;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I am an AI trained on 80,000 Hours articles. How can I help you plan your career today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg }),
      });

      if (!res.ok) {
        throw new Error(`Error: ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response, citations: data.citations }]);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Sorry, an error occurred: ${msg}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const examples = [
    "What skills will be most in demand in the next 5–10 years?",
    "How can I work on the world's most pressing problems?",
    "How do I figure out what I want to do with my life?",
  ];

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-[#0a0a0a] text-gray-900 dark:text-gray-100 font-sans selection:bg-gray-200 dark:selection:bg-gray-800">
      <header className="flex-none p-6 sticky top-0 bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-md z-10">
        <div className="max-w-3xl mx-auto flex items-center justify-center">
          <h1 className="text-lg font-medium tracking-tight">
            80,000 Hours AI
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 pb-32">
        <div className="max-w-3xl mx-auto space-y-10">
          {messages.map((msg, i) => (
            <div key={i} className="flex w-full">
              <div className="w-full">
                {msg.role === 'user' ? (
                  <div className="flex justify-end">
                    <p className="whitespace-pre-wrap leading-relaxed bg-gray-100 dark:bg-gray-800 px-5 py-3.5 rounded-3xl max-w-[85%] sm:max-w-[70%]">
                      {msg.content}
                    </p>
                  </div>
                ) : (
                  <div className="markdown-body text-[15px] leading-relaxed max-w-full">
                    <ReactMarkdown
                      // Default url transform strips the custom `citation:` scheme
                      // (returns ''), which would break our inline citation links.
                      urlTransform={(url) =>
                        url.startsWith('citation:') ? url : defaultUrlTransform(url)
                      }
                      components={{
                        a: ({ node, ...props }) => {
                          const href = props.href || '';
                          if (href.startsWith('citation:')) {
                            const id = parseInt(href.split(':')[1], 10);
                            const cit = msg.citations?.find(c => c.citation_id === id);
                            if (!cit) return <span className="text-gray-400">[{id}]</span>;
                            
                            const jumpHref = buildCitationHref(cit);
                            return (
                              <span className="relative group inline-block mx-0.5">
                                <a
                                  href={jumpHref}
                                  target="_blank"
                                  rel="noreferrer"
                                  title={cit.matched_text || cit.quote}
                                  className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-medium bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full no-underline transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400"
                                >
                                  {id}
                                </a>
                                <span className="block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-xl p-4 opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100 pointer-events-none group-hover:pointer-events-auto transition-all duration-200 z-50 origin-bottom">
                                  <span className="block text-sm text-gray-600 dark:text-gray-300 italic mb-3 line-clamp-4">
                                    "{cit.matched_text || cit.quote}"
                                  </span>
                                  <a href={jumpHref} target="_blank" rel="noreferrer" className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline block truncate no-underline">
                                    {cit.title} →
                                  </a>
                                  <span className="block absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white dark:bg-gray-900 border-b border-r border-gray-200 dark:border-gray-800 rotate-45"></span>
                                </span>
                              </span>
                            );
                          }
                          return <a {...props} className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" />;
                        }
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex w-full">
              <div className="flex items-center space-x-1.5 h-6">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-600 animate-pulse"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-600 animate-pulse delay-150"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-600 animate-pulse delay-300"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white dark:from-[#0a0a0a] dark:via-[#0a0a0a] to-transparent pt-10 pb-6 px-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 1 && (
            <div className="flex flex-wrap gap-2 justify-center mb-6">
              {examples.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setInput(ex)}
                  className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 text-gray-600 dark:text-gray-300 text-sm py-2 px-4 rounded-xl transition-all"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
          <form onSubmit={handleSubmit} className="relative flex items-center shadow-sm">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about career planning..."
              className="w-full bg-gray-100 dark:bg-gray-800 border-none text-gray-900 dark:text-white rounded-3xl py-4 pl-6 pr-14 focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-600"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 p-2 bg-black dark:bg-white hover:opacity-80 disabled:opacity-30 disabled:hover:opacity-30 text-white dark:text-black rounded-full transition-opacity flex items-center justify-center w-10 h-10"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 ml-0.5">
                <path d="m5 12 7-7 7 7"/>
                <path d="M12 19V5"/>
              </svg>
            </button>
          </form>
          <div className="text-center">
            <p className="text-[11px] text-gray-500">
              AI can make mistakes. Responses are generated based on 80,000 Hours content.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
