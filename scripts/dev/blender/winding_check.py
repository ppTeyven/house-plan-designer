"""绕序验证 —— 用【解析几何】证明哪种环顺序的绕序是对的。

【背景】
soft_slab 的底面封盖环顺序写反，导致相邻面带自相重叠、
法线完全反向（dot = -1.0000）。但"改对"不能凭直觉，
必须用可验证的判据。

【判据：右手定则 + 面法线必须背离实体】
对一段环（相邻两圈，半径 r0 → r1，高度 z0 → z1），
面带的一个四边形取顶点：
    v0 = (r0·cosθ, r0·sinθ, z0)
    v1 = (r0·cosθ₂, r0·sinθ₂, z0)
    v2 = (r1·cosθ₂, r1·sinθ₂, z1)
    v3 = (r1·cosθ,  r1·sinθ,  z1)
由_pydata(verts, [], faces) 的面绕序 (v0,v1,v2,v3)，
法线 = (v1-v0) × (v2-v0)。

取 θ=0 附近、θ₂ = θ + Δ（Δ>0，逆时针）：
    v1-v0 ≈ (0, r0·Δ, 0)          → 切向 +Y
    v2-v0 ≈ (r1-r0, r1·Δ, z1-z0)
    n = (v1-v0) × (v2-v0)
      = (r0·Δ·(z1-z0), -r0·Δ·(r1-r0), -r0·Δ·r1·Δ)
      ≈ (r0·Δ·Δz, -r0·Δ·Δr, 0)

分两种情况：
  A. 底面封盖：环在 z = -hz（恒定），Δz = 0，Δr = r1 - r0
     n ≈ (0, -r0·Δ·Δr, 0)
     实体内部在 +Y 方向（环心侧）？不 —— 底面封盖是"由外圈向内圈收"，
     即 r1 < r0（Δr < 0）→ n_y = -r0·Δ·Δr > 0 → 法线 +Y（切向外）
     ❌ 错误：底面法线应指向 -Z（朝下）。

     若改为 r1 > r0（由内圈往外走，Δr > 0）→ n_y < 0 → 法线 -Y（朝内）
     对底面而言，法线朝内/朝下才对（实体在环的上方）。

  B. 顶面封盖：环在 z = +hz（恒定），Δz = 0
     顶面是从外圈向内收（r1 < r0，Δr < 0）→ n_y > 0 → 法线 +Y（朝外）
     ✔ 顶面法线应朝上 +Z...

【重要修正】
环在同一 z 平面内时，四边形退化成【平面的环带】，
其法线是径向的（±Y），而不是 ±Z！
底面/顶面的"朝下/朝上"方向由【扇形中心点三角形】决定，
不是由环带决定。

所以：
  · 环带（侧壁、底盖环带、顶盖环带）法线是径向 → 判断标准：
      侧壁（Δr≈0, Δz>0）→ n ≈ (0,0,-r0·Δ²) → 法线 -Z（朝下）
      ⚠ 侧壁法线朝下？！这需要复核。
  · 中心扇形三角（top_c / bot_c）法线才是 ±Z。

本脚本用真实数值算，不靠推导结论。
用法：blender --background --python winding_check.py
"""
import mathutils
import math


def face_normal(v0, v1, v2, v3):
    a = mathutils.Vector(v1) - mathutils.Vector(v0)
    b = mathutils.Vector(v2) - mathutils.Vector(v0)
    n = a.cross(b)
    if n.length < 1e-12:
        return None
    return n.normalized()


def band_normal(r0, r1, z0, z1, theta=0.0, dtheta=0.02):
    """环带面 (v0,v1,v2,v3) 的法线，v0/r0@θ, v1/r0@θ+d, v2/r1@θ+d, v3/r1@θ"""
    def P(r, z, t):
        return (r * math.cos(t), r * math.sin(t), z)
    v0 = P(r0, z0, theta)
    v1 = P(r0, z0, theta + dtheta)
    v2 = P(r1, z1, theta + dtheta)
    v3 = P(r1, z1, theta)
    return face_normal(v0, v1, v2, v3)


def fan_normal(r, z_ring, z_center, theta=0.0, dtheta=0.02, up=True):
    """中心扇形三角 (center, ring[i], ring[i+1]) 的法线"""
    c = (0.0, 0.0, z_center)
    p0 = (r * math.cos(theta), r * math.sin(theta), z_ring)
    p1 = (r * math.cos(theta + dtheta), r * math.sin(theta + dtheta), z_ring)
    if up:
        return face_normal(c, p0, p1)
    return face_normal(c, p1, p0)


print("=" * 92)
print("环带/扇形法线数值验证（r0=0.30 → r1, z0 → z1）")
print("=" * 92)
print("%-34s %-26s %s" % ("情形", "法线", "判定"))

print()
print("--- 底面封盖环带（z 恒定 = -0.11）---")
for r1, label in ((0.20, "由外向内收 (r1 < r0)  [原代码]"),
                  (0.40, "由内向外走 (r1 > r0)  [新代码]")):
    n = band_normal(0.30, r1, -0.11, -0.11)
    print("%-34s (%6.3f,%6.3f,%6.3f)   径向%s"
          % (label, n.x, n.y, n.z, "朝外" if n.y > 0 else "朝内"))

print()
print("--- 侧壁环带（r 恒定 = 0.30, z 从下到上）---")
for z1, label in ((0.05, "侧壁向上 (z1 > z0)"),
                  (-0.05, "侧壁向下 (z1 < z0)")):
    n = band_normal(0.30, 0.30, -0.11, z1)
    print("%-34s (%6.3f,%6.3f,%6.3f)   朝%s"
          % (label, n.x, n.y, n.z, "上" if n.z > 0 else "下"))

print()
print("--- 顶面封盖环带（z 恒定 = +0.11）---")
for r1, label in ((0.20, "由外向内收 (r1 < r0)  [原代码]"),
                  (0.40, "由内向外走 (r1 > r0)")):
    n = band_normal(0.30, r1, 0.11, 0.11)
    print("%-34s (%6.3f,%6.3f,%6.3f)   径向%s"
          % (label, n.x, n.y, n.z, "朝外" if n.y > 0 else "朝内"))

print()
print("--- 中心扇形三角（决定顶/底面法线朝向）---")
n_up = fan_normal(0.20, 0.11, 0.11, up=True)
print("%-34s (%6.3f,%6.3f,%6.3f)" % ("顶面 center,ring,ring [原代码]", n_up.x, n_up.y, n_up.z))
n_dn = fan_normal(0.20, -0.11, -0.11, up=False)
print("%-34s (%6.3f,%6.3f,%6.3f)" % ("底面 center,ring[+1],ring [原代码]", n_dn.x, n_dn.y, n_dn.z))

print()
print("--- 结论参考 ---")
print("实体是'上下都有盖、中间侧壁'的封闭体：")
print("  顶盖所有面法线应朝上（+Z 方向分量占优）")
print("  底盖所有面法线应朝下（-Z 方向分量占优）")
print("  侧壁所有面法线应朝外（径向）")
