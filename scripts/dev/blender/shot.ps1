param(
    [string]$Out = "D:\house planner\house-plan-designer-main\scripts\dev\_previews\_screen.png",
    [string]$WindowTitleLike = ""
)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

if ($WindowTitleLike) {
    $p = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitleLike*" } |
         Sort-Object { $_.MainWindowHandle } | Select-Object -First 1
    if ($p) {
        Add-Type @"
using System;using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@
        # 最大化（SW_MAXIMIZE=3），这样抓到的就是全屏视口，没有黑边
        [void][W]::ShowWindow($p.MainWindowHandle, 3)
        Start-Sleep -Milliseconds 900
        $r = New-Object W+RECT
        [void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
        $x = $r.L; $y = $r.T; $w = $r.R - $r.L; $h = $r.B - $r.T
        if ($w -le 0 -or $h -le 0) { $x = 0; $y = 0; $w = 1920; $h = 1080 }
    } else { $x = 0; $y = 0; $w = 1920; $h = 1080 }
} else {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $x = $b.X; $y = $b.Y; $w = $b.Width; $h = $b.Height
}

$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($x, $y, 0, 0, (New-Object System.Drawing.Size $w, $h))
$g.Dispose()
$dir = Split-Path $Out -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "SAVED $Out ($w x $h)"
