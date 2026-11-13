# Open E-Pin

An open-source, battery-powered e-ink pin for a backpack or jacket. It has a small round
colour e-paper display and Bluetooth Low Energy. An Android app sends it new images.

| | |
|---|---|
| Display | Good Display GDEH0169E02, 1.69" round, 400 x 400, 6 colours (Spectra 6), 32-pin FPC |
| Radio / MCU | Raytac MDBT50Q-1MV2 (Nordic nRF52840), pre-certified module |
| Battery | 3.7 V LiPo, 60 mAh, JST-PH, charged over USB-C at 30 mA |
| Board | 56 mm round with a flat for the display ribbon, 4 layers, all parts on the back |
| Case | 3D-printed, 60.4 mm across, 10.75 mm thick, 2 M2 screws from the back into heat-set inserts in the bezel, plus 2 snap hooks, two locking pin-back posts on the back |

**Status: hardware v0.1, work in progress.** The schematic, placement and routing are
done, and a printable case has been modelled and fit-checked against every part. Nothing has
been built or tested yet. Do not order boards from this revision.

## Repository layout

- [`hardware/`](hardware/): KiCad 7 project, the scripts that generate it, BOM and docs
- [`hardware/case/`](hardware/case/): printed case (SolidCraft design, STEP/STL, fit check, fasteners)
- `firmware/`: not started
- `app/`: Android app, not started

## License

GPL-3.0, see [LICENSE](LICENSE).
