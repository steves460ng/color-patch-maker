<p align="center">
  <img src="docs/assets/icon.png" width="112" alt="Color Patch Maker icon">
</p>

<h1 align="center">Color Patch Maker</h1>

<p align="center">
  <b>English</b> · <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  CMYK patch charts that get you to the right color, printing only what you need
</p>

<p align="center">
  <a href="https://drive.google.com/file/d/1jVFRYr7_GB6gT_6guhcR8KIbclYbl9Ag/view?usp=sharing"><b>Download for Windows</b></a> · Windows 10/11 x64 · ZIP, about 87 MB
</p>

<p align="center">
  <img src="docs/ui/screens/1600x900-selected.png" width="100%" alt="Color Patch Maker window: settings on the left, a 7×7 patch preview on the right">
</p>

When a printed color doesn't match the physical sample, nudging the numbers and reprinting over and over gets tedious. Enter the original CMYK value, and Color Patch Maker builds a print-ready PDF chart of nearby colors laid out by rules you choose. Put the print next to the sample, pick the closest patch, and use the CMYK value printed under it.

The app's interface is in Korean. Screen names in this guide are given in English with the Korean label in parentheses.

## How it works

1. Enter the CMYK value of the color you want to match.
2. Choose a patch mode and step, and check the layout in the preview.
3. Create the PDF and print it.
4. Compare it with the physical sample and pick the closest patch.
5. Use that value, or click the patch in the preview to make it the new starting point and print again.

## Two patch modes

### Two-channel grid (두 채널 격자)

Keeps the base color in the middle and changes two channels across and down in fixed steps. The other two channels stay the same. Use it when you want to adjust two channels together, such as "a little less magenta and a little more cyan".

- Channel pairs: CM, CY, CK, MY, MK, YK
- Step: any whole number from 1 percentage point
- Size: columns and rows set separately, 7×7 by default

<p align="center">
  <img src="docs/ui/screens/1600x900-grid.png" width="100%" alt="Two-channel grid preview">
</p>

### Start–end ramp (시작·끝 보간)

Divides the range between a start color and an end color evenly into the number of patches you choose. All four channels change together, so use it when three or more channels need adjusting, or to look closely at the range between two candidates you picked earlier.

Example: C40 M70 Y20 K0 → C30 M75 Y30 K5, 11 patches

| Patch | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | 40 | 39 | 38 | 37 | 36 | 35 | 34 | 33 | 32 | 31 | 30 |
| M | 70 | 71 | 71 | 72 | 72 | 73 | 73 | 74 | 74 | 75 | 75 |
| Y | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 |
| K | 0 | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 |

<p align="center">
  <img src="docs/ui/screens/1600x900-ramp.png" width="100%" alt="Start–end ramp preview">
</p>

## Output built for the print shop

- **Whole-number CMYK only.** The printer outputs whole numbers, so every patch value and label is a whole number. Decimals are rejected with a message, never rounded.
- **One file, one page.** Works with RIPs that can't separate pages. When the patches don't fit on one sheet, they are split into several single-page PDFs named `_01`, `_02`, and so on.
- **Every patch is labeled with its CMYK value,** ready to read off the print. The base color and the ramp's start and end are marked.
- **Colors are saved as vectors and checked again.** Every patch is written as a DeviceCMYK vector, and the PDF is read back to confirm the values and positions.
- **Existing files are never overwritten.** File names carry the input values (for example `C40_M70_Y20_K0_CM_s1.pdf`), and `_v2` is added if the name is taken.
- **Values beyond 0–100% are held at 0 and 100.** If the edge of a grid goes out of range, you get a warning, and patches that end up with the same value are still printed.

## The window

| Area | What it does |
| --- | --- |
| Mode tabs | Switch between the two-channel grid and the start–end ramp. Each tab keeps its own inputs. |
| Settings | Enter CMYK, step and patch counts. Invalid values are flagged right under the field. |
| Layout (레이아웃) | Set the sheet (305×505 mm by default), margin (20 mm by default), patch size (auto or mm) and patch spacing. |
| Preview | Shows the patch layout at the sheet's true proportions, with page buttons when the output spans several sheets. |
| Selected patch (선택한 패치) | Shows the values of the patch you clicked and puts them into the next run as the base, start or end. |
| Notices and save | Show warnings and results, and create the PDF in the folder you choose. |

The window stays responsive while the PDF is being made. When it finishes, you see the list of files and the check result, and **Open folder** (폴더 열기) takes you straight there. The save folder and layout settings come back the next time you open the app.

Expand Layout to choose **Default** (기본, 305×505 mm) or **Card** (카드, 85.6×54 mm). Save the sheet, margin, spacing and patch size you use often under a name with **Save template** (템플릿 저장). Saving over an existing name asks first, and only templates you created can be deleted. **Reset to defaults** (기본값으로 되돌리기) resets only the layout and keeps your colors, patch counts and save folder.

The Card template uses a 2 mm margin and 18 mm patches, fitting up to 8 patches (4×2) per card. A 7×7 grid becomes 8 PDFs and a 3×3 grid becomes 2, with labels for every CMYK value.

## Command line

For repeated jobs, the same features are available in the command-line program `cpm.exe`, which is included in the download.

```powershell
cpm.exe grid --cmyk 40 70 20 0 --channels CM --step 1 --cols 7 --rows 7 --out-dir output
cpm.exe ramp --from 40 70 20 0 --to 30 75 30 5 --count 11 --out-dir output
cpm.exe verify output\C40_M70_Y20_K0_CM_s1.pdf output\C40_M70_Y20_K0_CM_s1.json
```

Use `--template card` for the card layout, or `--template default`. Any `--paper`, `--margin`, `--gap` or `--patch-size` you add takes priority over the template. Templates you saved yourself are available in the app only.

```powershell
cpm.exe grid --cmyk 40 70 20 0 --cols 3 --rows 3 --template card --out-dir cards
```

## Download and install

For Windows 10/11 x64. There is no installer; just unzip and run.

1. [Download ColorPatchMaker.zip](https://drive.google.com/file/d/1jVFRYr7_GB6gT_6guhcR8KIbclYbl9Ag/view?usp=sharing) (Google Drive, about 87 MB)
2. Unzip it wherever you like.
3. Run `ColorPatchMaker.exe` from the unzipped folder. The command-line program `cpm.exe` is included too.

- Don't move the program file on its own. It needs the `_internal` folder next to it, so move the whole folder. To start it from the desktop, use a shortcut instead of a copy.
- The program isn't signed, so Windows may show "Windows protected your PC" the first time. Choose **More info → Run anyway**. If your work PC blocks it, ask your administrator.
- You don't need to install Python.

## Good to know

- Colors on screen are for reference only. Always judge color from the print.
- The CMYK values stored in the PDF are checked, but a RIP or printer may still change the color, and that can't be guaranteed.
- Prints have no header, only one line of CMYK values under each patch. The base color is marked `*` and the ramp's start and end `>` and `<`. Patch IDs appear in the app when you select a patch.
- Labels shrink from 7 pt to as small as 4.5 pt to fit the patch. At 4.5 pt a loupe helps. If even that size doesn't fit, the app asks you to make the patches larger or use fewer of them.
