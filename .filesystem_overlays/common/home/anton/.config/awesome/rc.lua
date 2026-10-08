-- Load the system default config (survives package updates)
dofile("/etc/xdg/awesome/rc.lua")

-- Custom keybindings (appended to the system defaults)
local awful = require("awful")
local gears = require("gears")

root.keys(gears.table.join(root.keys(),
    awful.key({ modkey,           }, "Tab", function ()
        awful.client.focus.byidx(-1)
        if client.focus then client.focus:raise() end
    end, {description = "focus previous client", group = "client"}),

    awful.key({ modkey, "Shift"   }, "Tab", function ()
        awful.client.focus.byidx(1)
        if client.focus then client.focus:raise() end
    end, {description = "focus next client", group = "client"})
))

-- Override wallpaper on all screens
local function set_custom_wallpaper(s)
    gears.wallpaper.maximized(os.getenv("HOME") .. "/wallpaper_1920x1200.png", s, true)
end

screen.connect_signal("property::geometry", set_custom_wallpaper)
for s in screen do
    set_custom_wallpaper(s)
end
