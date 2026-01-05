import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import useWebSocket from 'react-use-websocket'
import './ChatInterface.css'

const API_URL = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/ws'

function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mood, setMood] = useState('OBSERVANT')
  const [stats, setStats] = useState({ cpu: 0, ram: 0, battery: 100 })
  const messagesEndRef = useRef(null)

  // WebSocket connection for autonomous thoughts
  const { lastJsonMessage, readyState } = useWebSocket(WS_URL, {
    shouldReconnect: () => true,
    reconnectInterval: 3000
  })

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle autonomous thoughts from WebSocket
  useEffect(() => {
    if (lastJsonMessage && lastJsonMessage.type === 'autonomous') {
      const autonomousMessage = {
        type: 'autonomous',
        text: lastJsonMessage.text,
        mood: lastJsonMessage.mood,
        trigger: lastJsonMessage.trigger,
        timestamp: new Date().toLocaleTimeString()
      }
      setMessages(prev => [...prev, autonomousMessage])
      setMood(lastJsonMessage.mood)
      if (lastJsonMessage.stats) {
        setStats(lastJsonMessage.stats)
      }
    }
  }, [lastJsonMessage])

  // Send message to backend
  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = {
      type: 'user',
      text: input,
      timestamp: new Date().toLocaleTimeString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post(`${API_URL}/chat`, { text: input })
      const data = response.data

      const botMessage = {
        type: 'agent',
        text: data.response,
        mood: data.mood,
        tool_used: data.tool_used,
        success: data.success,
        timestamp: new Date().toLocaleTimeString()
      }

      setMessages(prev => [...prev, botMessage])
      setMood(data.mood)
      setStats(data.stats)
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        type: 'error',
        text: 'Connection to Ultron Core failed.',
        timestamp: new Date().toLocaleTimeString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const getConnectionStatus = () => {
    switch (readyState) {
      case 0: return '🔴 CONNECTING'
      case 1: return '🟢 ONLINE'
      case 2: return '🟡 CLOSING'
      case 3: return '🔴 OFFLINE'
      default: return '⚪ UNKNOWN'
    }
  }

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <h1 className="title">U L T R O N</h1>
          <span className="version">v5.7 - DESKTOP PRESENCE</span>
        </div>
        <div className="header-right">
          <div className="status-badge">{getConnectionStatus()}</div>
          <div className="mood-badge">{mood}</div>
        </div>
      </div>

      {/* System Stats Bar */}
      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-label">CPU:</span>
          <span className="stat-value">{stats.cpu?.toFixed(1)}%</span>
          <div className="stat-bar">
            <div className="stat-fill" style={{ width: `${stats.cpu}%` }}></div>
          </div>
        </div>
        <div className="stat-item">
          <span className="stat-label">RAM:</span>
          <span className="stat-value">{stats.ram?.toFixed(1)}%</span>
          <div className="stat-bar">
            <div className="stat-fill" style={{ width: `${stats.ram}%` }}></div>
          </div>
        </div>
        <div className="stat-item">
          <span className="stat-label">BATT:</span>
          <span className="stat-value">{stats.battery?.toFixed(0)}%</span>
          <div className="stat-bar">
            <div className="stat-fill battery" style={{ width: `${stats.battery}%` }}></div>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="messages-area">
        {messages.length === 0 && (
          <div className="welcome-message">
            <div className="ascii-logo">
╔════════════════════════════════════════╗
║        U L T R O N   S Y S T E M       ║
║      COGNITIVE CORE INITIALIZED        ║
╚════════════════════════════════════════╝
            </div>
            <p className="welcome-text">Awaiting directives...</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div className="message-header">
              <span className="message-sender">
                {msg.type === 'user' ? '👤 USER' : 
                 msg.type === 'autonomous' ? `🤖 ULTRON [${msg.trigger?.toUpperCase()}]` :
                 msg.type === 'error' ? '⚠️ ERROR' :
                 `🤖 ULTRON [${msg.mood}]`}
              </span>
              <span className="message-time">{msg.timestamp}</span>
            </div>
            <div className="message-content">
              {msg.text}
              {msg.tool_used && msg.tool_used !== 'none' && (
                <span className="tool-badge">{msg.tool_used}</span>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <textarea
          className="message-input"
          placeholder="Enter directive..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          rows={1}
        />
        <button 
          className="send-button" 
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          {loading ? '⏳' : '▶'}
        </button>
      </div>
    </div>
  )
}

export default ChatInterface
