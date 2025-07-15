"use client"

import { Button } from "@/components/ui/button"
import { X } from "lucide-react"
import { useState } from "react"

export default function AuthPage() {
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/auth/x/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        throw new Error('Failed to initiate X login')
      }
      
      const data = await response.json()
      
      // Redirect to X.com authorization page
      window.location.href = data.auth_url
      
    } catch (error) {
      console.error('X login error:', error)
      alert('Failed to start X login. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-foreground mb-2">Welcome to T-Pot Run Club</h1>
          <p className="text-muted-foreground">Sign in with X to access your running leaderboard</p>
        </div>
        
        <Button 
          onClick={handleLogin}
          disabled={loading}
          size="lg"
          className="flex items-center gap-2 px-8 py-3 text-lg"
        >
          <X className="size-5" />
          {loading ? 'Connecting...' : 'Login with X'}
        </Button>
      </div>
    </div>
  )
}
