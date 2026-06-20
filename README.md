# Lightshow

Python script to control case lights via
[OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB),
[openrgb-python](https://github.com/jath03/openrgb-python), and
[schedule](https://github.com/dbader/schedule).

Includes a systemd service definition.

## Network feedback

On Metatron, the lights reflect the router's WAN routing state:

- Fiber primary: normal day/night behavior.
- LTE fallback: amber strobe.
- No usable WAN route: red strobe.

The script does not run its own internet probe. It reads
`metatron-wan-failover.service` health and the default routes owned by
Metatron's network stack, including the temporary `igc0` metric-50 route that
marks active LTE failover.
