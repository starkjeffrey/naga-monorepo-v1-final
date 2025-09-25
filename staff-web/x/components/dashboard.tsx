"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Users, TrendingUp, FileCheck, Calendar, BookOpen, Globe, Award } from "lucide-react"

const studentTrendData = [
  { month: "Jan", students: 2400 },
  { month: "Feb", students: 2600 },
  { month: "Mar", students: 2800 },
  { month: "Apr", students: 3200 },
  { month: "May", students: 3400 },
  { month: "Jun", students: 3600 },
  { month: "Jul", students: 3800 },
  { month: "Aug", students: 4200 },
  { month: "Sep", students: 4400 },
  { month: "Oct", students: 4600 },
  { month: "Nov", students: 4800 },
  { month: "Dec", students: 5000 },
]

const upcomingEvents = [
  { date: "Dec 15", event: "TOEFL Test Session", type: "exam" },
  { date: "Dec 18", event: "Winter Graduation Ceremony", type: "ceremony" },
  { date: "Dec 20", event: "International Student Orientation", type: "orientation" },
  { date: "Dec 22", event: "Faculty Meeting", type: "meeting" },
  { date: "Jan 8", event: "Spring Semester Begins", type: "academic" },
]

export function Dashboard() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-balance">Dashboard Overview</h1>
          <p className="text-muted-foreground text-pretty">Welcome back to Dragon Academy management system</p>
        </div>
        <Badge variant="secondary" className="text-sm">
          Academic Year 2024-2025
        </Badge>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5,247</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-chart-2">+12.5%</span> from last semester
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Growth Trend</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+247</div>
            <p className="text-xs text-muted-foreground">New enrollments this month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Test Takers</CardTitle>
            <FileCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">342</div>
            <p className="text-xs text-muted-foreground">Language tests this week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Next Event</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Dec 15</div>
            <p className="text-xs text-muted-foreground">TOEFL Test Session</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Student Trend Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Student Enrollment Trend</CardTitle>
            <CardDescription>Monthly student enrollment over the past year</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{
                students: {
                  label: "Students",
                  color: "hsl(var(--chart-1))",
                },
              }}
              className="h-[300px]"
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={studentTrendData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" className="text-muted-foreground" fontSize={12} />
                  <YAxis className="text-muted-foreground" fontSize={12} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line
                    type="monotone"
                    dataKey="students"
                    stroke="var(--color-chart-1)"
                    strokeWidth={2}
                    dot={{ fill: "var(--color-chart-1)", strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: "var(--color-chart-1)", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Upcoming Events */}
        <Card>
          <CardHeader>
            <CardTitle>Key Events</CardTitle>
            <CardDescription>Upcoming important dates and events</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {upcomingEvents.map((event, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-pretty">{event.event}</p>
                  <p className="text-xs text-muted-foreground">{event.date}</p>
                </div>
                <Badge
                  variant={event.type === "exam" ? "destructive" : event.type === "ceremony" ? "default" : "secondary"}
                  className="text-xs"
                >
                  {event.type}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Department Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-chart-1/10 to-chart-1/5 border-chart-1/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">English Dept.</p>
                <p className="text-2xl font-bold">1,847</p>
              </div>
              <div className="h-12 w-12 bg-chart-1/20 rounded-lg flex items-center justify-center">
                <BookOpen className="h-6 w-6 text-chart-1" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-chart-2/10 to-chart-2/5 border-chart-2/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Mandarin Dept.</p>
                <p className="text-2xl font-bold">1,234</p>
              </div>
              <div className="h-12 w-12 bg-chart-2/20 rounded-lg flex items-center justify-center">
                <Globe className="h-6 w-6 text-chart-2" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-chart-3/10 to-chart-3/5 border-chart-3/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Spanish Dept.</p>
                <p className="text-2xl font-bold">892</p>
              </div>
              <div className="h-12 w-12 bg-chart-3/20 rounded-lg flex items-center justify-center">
                <Users className="h-6 w-6 text-chart-3" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-chart-4/10 to-chart-4/5 border-chart-4/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Other Languages</p>
                <p className="text-2xl font-bold">1,274</p>
              </div>
              <div className="h-12 w-12 bg-chart-4/20 rounded-lg flex items-center justify-center">
                <Award className="h-6 w-6 text-chart-4" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
