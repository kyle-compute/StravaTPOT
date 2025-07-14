"use client"

import { Button } from "@/components/ui/button"
import { X } from "lucide-react"

export default function AuthPage() {
  const handleLogin = () => {
    // Add your X/Twitter OAuth login logic here
    console.log("Login with X clicked")
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-foreground mb-2">Welcome</h1>
          <p className="text-muted-foreground">Sign in to continue</p>
        </div>
        
        <Button 
          onClick={handleLogin}
          size="lg"
          className="flex items-center gap-2 px-8 py-3 text-lg"
        >
          <X className="size-5" />
          Login with X
        </Button>
      </div>
    </div>
  )
}
