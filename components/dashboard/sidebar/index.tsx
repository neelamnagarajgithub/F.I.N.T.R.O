"use client"

import type * as React from "react"
import Link from "next/link"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import BracketsIcon from "@/components/icons/brackets"
import TrendUpIcon from "@/components/icons/trend-up"
import AlertIcon from "@/components/icons/alert"
import DollarIcon from "@/components/icons/dollar"
import MonkeyIcon from "@/components/icons/monkey"
import DotsVerticalIcon from "@/components/icons/dots-vertical"
import GearIcon from "@/components/icons/gear"
import { Bullet } from "@/components/ui/bullet"
import Image from "next/image"
import { useIsV0 } from "@/lib/v0-context"
import { usePathname } from "next/navigation"

const data = {
  navMain: [
    {
      title: "CFO Dashboard",
      items: [
        {
          title: "Executive Overview",
          url: "/dashboard", // Updated to /dashboard route
          icon: BracketsIcon,
        },
        {
          title: "Cashflow & Forecast",
          url: "/dashboard/cashflow", // Updated to /dashboard route
          icon: TrendUpIcon,
        },
        {
          title: "Risk & Anomalies",
          url: "/dashboard/risk", // Updated to /dashboard route
          icon: AlertIcon,
        },
        {
          title: "Liquidity & Collisions",
          url: "/dashboard/liquidity", // Updated to /dashboard route
          icon: DollarIcon,
        },
        {
          title: "Collections",
          url: "/dashboard/collections", // Updated to /dashboard route
          icon: DollarIcon,
        },
        {
          title: "Scenario Simulator",
          url: "/dashboard/simulator", // Updated to /dashboard route
          icon: BracketsIcon,
        },
        {
          title: "Autonomous Execution",
          url: "/dashboard/execution", // Updated to /dashboard route
          icon: MonkeyIcon,
        },
        {
          title: "Reports & Exports",
          url: "/dashboard/reports", // Updated to /dashboard route
          icon: BracketsIcon,
        },
        {
          title: "Settings",
          url: "/dashboard/settings", // Updated to /dashboard route
          icon: GearIcon,
        },
      ],
    },
  ],
  user: {
    name: "CFO",
    email: "cfo@company.com",
    avatar: "/avatars/user_krimson.png",
  },
}

export function DashboardSidebar({ className, ...props }: React.ComponentProps<typeof Sidebar>) {
  const isV0 = useIsV0()
  const pathname = usePathname()

  return (
    <Sidebar {...props} className={cn("py-sides", className)}>
      <SidebarHeader className="rounded-t-lg flex gap-3 flex-row rounded-b-none">
        <div className="flex overflow-clip size-12 shrink-0 items-center justify-center rounded bg-sidebar-primary-foreground/10 transition-colors group-hover:bg-sidebar-primary text-sidebar-primary-foreground">
          <MonkeyIcon className="size-10 group-hover:scale-[1.7] origin-top-left transition-transform" />
        </div>
        <div className="grid flex-1 text-left text-sm leading-tight">
          <span className="text-2xl font-display">F.I.N.T.R.O</span>
          <span className="text-xs uppercase">CFO Dashboard</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {data.navMain.map((group, i) => (
          <SidebarGroup className={cn(i === 0 && "rounded-t-none")} key={group.title}>
            <SidebarGroupLabel>
              <Bullet className="mr-2" />
              {group.title}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={pathname === item.url}>
                      <Link href={item.url}>
                        <item.icon className="size-5" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="p-0">
        <SidebarGroup>
          <SidebarGroupLabel>
            <Bullet className="mr-2" />
            User
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <Popover>
                  <PopoverTrigger className="flex gap-0.5 w-full group cursor-pointer">
                    <div className="shrink-0 flex size-14 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground overflow-clip">
                      <Image
                        src={data.user.avatar || "/placeholder.svg"}
                        alt={data.user.name}
                        width={120}
                        height={120}
                      />
                    </div>
                    <div className="group/item pl-3 pr-1.5 pt-2 pb-1.5 flex-1 flex bg-sidebar-accent hover:bg-sidebar-accent-active/75 items-center rounded group-data-[state=open]:bg-sidebar-accent-active group-data-[state=open]:hover:bg-sidebar-accent-active group-data-[state=open]:text-sidebar-accent-foreground">
                      <div className="grid flex-1 text-left text-sm leading-tight">
                        <span className="truncate text-xl font-display">{data.user.name}</span>
                        <span className="truncate text-xs uppercase opacity-50 group-hover/item:opacity-100">
                          {data.user.email}
                        </span>
                      </div>
                      <DotsVerticalIcon className="ml-auto size-4" />
                    </div>
                  </PopoverTrigger>
                  <PopoverContent className="w-56 p-0" side="bottom" align="end" sideOffset={4}>
                    <div className="flex flex-col">
                      <button className="flex items-center px-4 py-2 text-sm hover:bg-accent">
                        <MonkeyIcon className="mr-2 h-4 w-4" />
                        Account
                      </button>
                      <button className="flex items-center px-4 py-2 text-sm hover:bg-accent">
                        <GearIcon className="mr-2 h-4 w-4" />
                        Settings
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
