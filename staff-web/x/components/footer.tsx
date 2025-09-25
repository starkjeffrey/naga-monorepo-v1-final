"use client"

import { Button } from "@/components/ui/button"
import { Globe, Sun, MessageSquare } from "lucide-react"

export function Footer() {
  return (
    <footer className="h-16 bg-card border-t border-border flex items-center justify-between px-6 mt-auto">
      <div className="flex items-center gap-4">
        <p className="text-sm text-muted-foreground">© 2025 Dragon Academy. All rights reserved.</p>
        <div className="h-4 w-px bg-border" />
        <p className="text-sm text-muted-foreground">Language & Cultural Institute</p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <Globe className="h-4 w-4" />
          <span className="sr-only">Language</span>
        </Button>

        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <Sun className="h-4 w-4" />
          <span className="sr-only">Theme</span>
        </Button>

        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <MessageSquare className="h-4 w-4" />
          <span className="sr-only">Messages</span>
        </Button>
      </div>
    </footer>
  )
}
