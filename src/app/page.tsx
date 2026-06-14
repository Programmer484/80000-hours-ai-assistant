'use client';

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

type Message = {
  role: 'user' | 'assistant';
  content: string;
};

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
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Sorry, an error occurred: ${error.message}` },
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
    <div className="flex flex-col h-screen bg-black">
      <header className="flex-none p-6 border-b border-gray-800 bg-gray-950">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              80,000 Hours Q&A
            </h1>
            <p className="text-gray-400 mt-1 text-sm font-medium">
              Get answers backed by citations from 80,000 Hours articles.
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 pb-32">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex w-full ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-4 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-none shadow-lg'
                    : 'bg-gray-800 text-gray-100 rounded-bl-none shadow-md border border-gray-700'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                ) : (
                  <div className="markdown-body text-[15px]">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex w-full justify-start">
              <div className="max-w-[85%] rounded-2xl px-5 py-4 bg-gray-800 text-gray-400 rounded-bl-none flex items-center space-x-2 border border-gray-700">
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-75"></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-150"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black to-transparent pt-10 pb-6 px-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 1 && (
            <div className="flex flex-wrap gap-2 justify-center mb-4">
              {examples.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setInput(ex)}
                  className="bg-gray-900 border border-gray-700 hover:border-gray-500 text-gray-300 text-sm py-2 px-4 rounded-full transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about career planning..."
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-full py-4 pl-6 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-lg"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-full transition-colors flex items-center justify-center w-10 h-10"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 ml-0.5">
                <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.404z" />
              </svg>
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
}
