
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { interviewAgentService } from '../../services/interviewAgentService';
import { Send, User, Bot, Loader2, ArrowLeft } from 'lucide-react';

const InterviewAgent = () => {
               const { jobId } = useParams();
               const navigate = useNavigate();
               const [sessionId, setSessionId] = useState(null);
               const [messages, setMessages] = useState([]);
               const [inputText, setInputText] = useState('');
               const [loading, setLoading] = useState(false);
               const [initializing, setInitializing] = useState(true);
               const messagesEndRef = useRef(null);

               // Initialize Session
               useEffect(() => {
                              const initSession = async () => {
                                             try {
                                                            const res = await interviewAgentService.startSession(jobId);
                                                            setSessionId(res.session_id);
                                                            // System greeting is implicitly handled by the backend history, 
                                                            // but we can add UI-only greeting or fetch history if endpoints supported it.
                                                            // For now, let's add a local welcome message.
                                                            setMessages([{
                                                                           role: 'assistant',
                                                                           content: "Hello! I'm your AI Interviewer. I've reviewed the job description. Ready to begin?"
                                                            }]);
                                             } catch (err) {
                                                            console.error("Failed to start session:", err);
                                                            alert("Failed to start interview session. Please try again.");
                                                            navigate(-1);
                                             } finally {
                                                            setInitializing(false);
                                             }
                              };

                              if (jobId) {
                                             initSession();
                              }
               }, [jobId, navigate]);

               // Auto-scroll to bottom
               useEffect(() => {
                              messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
               }, [messages]);

               const handleSend = async () => {
                              if (!inputText.trim() || !sessionId) return;

                              const userMsg = { role: 'user', content: inputText };
                              setMessages(prev => [...prev, userMsg]);
                              setInputText('');
                              setLoading(true);

                              try {
                                             const res = await interviewAgentService.chat(sessionId, userMsg.content);
                                             setMessages(prev => [...prev, { role: 'assistant', content: res.content }]);
                              } catch (err) {
                                             console.error("Chat error:", err);
                                             setMessages(prev => [...prev, { role: 'assistant', content: "I'm having trouble connecting. Please try again." }]);
                              } finally {
                                             setLoading(false);
                              }
               };

               if (initializing) {
                              return (
                                             <div className="flex h-screen items-center justify-center bg-gray-50">
                                                            <div className="text-center">
                                                                           <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
                                                                           <h2 className="text-xl font-semibold text-gray-800">Initializing Interview Environment...</h2>
                                                                           <p className="text-gray-500">Loading job context and preparing agent.</p>
                                                            </div>
                                             </div>
                              );
               }

               return (
                              <div className="flex flex-col h-screen bg-gray-50">
                                             {/* Header */}
                                             <div className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm">
                                                            <div className="flex items-center gap-4">
                                                                           <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-full">
                                                                                          <ArrowLeft className="h-5 w-5 text-gray-600" />
                                                                           </button>
                                                                           <div>
                                                                                          <h1 className="text-lg font-bold text-gray-800">AI Technical Interview</h1>
                                                                                          <p className="text-xs text-green-600 flex items-center gap-1">
                                                                                                         <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                                                                                         Live Session
                                                                                          </p>
                                                                           </div>
                                                            </div>
                                                            <div className="text-sm text-gray-500">
                                                                           Job ID: {jobId}
                                                            </div>
                                             </div>

                                             {/* Chat Area */}
                                             <div className="flex-1 overflow-y-auto p-6 space-y-6">
                                                            {messages.map((msg, idx) => (
                                                                           <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                                                                          <div className={`flex max-w-[80%] gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                                                                                         {/* Avatar */}
                                                                                                         <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-100' : 'bg-purple-100'
                                                                                                                        }`}>
                                                                                                                        {msg.role === 'user' ? <User className="h-6 w-6 text-blue-600" /> : <Bot className="h-6 w-6 text-purple-600" />}
                                                                                                         </div>

                                                                                                         {/* Bubble */}
                                                                                                         <div className={`p-4 rounded-2xl shadow-sm text-sm leading-relaxed ${msg.role === 'user'
                                                                                                                                       ? 'bg-blue-600 text-white rounded-tr-none'
                                                                                                                                       : 'bg-white text-gray-800 border rounded-tl-none'
                                                                                                                        }`}>
                                                                                                                        {msg.content}
                                                                                                         </div>
                                                                                          </div>
                                                                           </div>
                                                            ))}

                                                            {loading && (
                                                                           <div className="flex justify-start">
                                                                                          <div className="flex gap-3 max-w-[80%]">
                                                                                                         <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                                                                                                                        <Bot className="h-6 w-6 text-purple-600" />
                                                                                                         </div>
                                                                                                         <div className="bg-white p-4 rounded-2xl rounded-tl-none border shadow-sm flex items-center gap-2">
                                                                                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                                                                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                                                                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                                                                                                         </div>
                                                                                          </div>
                                                                           </div>
                                                            )}
                                                            <div ref={messagesEndRef} />
                                             </div>

                                             {/* Input Area */}
                                             <div className="bg-white border-t p-4">
                                                            <div className="max-w-4xl mx-auto flex gap-4">
                                                                           <input
                                                                                          type="text"
                                                                                          value={inputText}
                                                                                          onChange={(e) => setInputText(e.target.value)}
                                                                                          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                                                                          placeholder="Type your answer..."
                                                                                          className="flex-1 px-4 py-3 bg-gray-50 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                                                          disabled={loading}
                                                                           />
                                                                           <button
                                                                                          onClick={handleSend}
                                                                                          disabled={loading || !inputText.trim()}
                                                                                          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-xl transition-colors flex items-center gap-2 font-medium"
                                                                           >
                                                                                          <Send className="h-4 w-4" />
                                                                                          Send
                                                                           </button>
                                                            </div>
                                             </div>
                              </div>
               );
};

export default InterviewAgent;
