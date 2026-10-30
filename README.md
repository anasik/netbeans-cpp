# C/C++ Support for Apache NetBeans 31

Reproducible packaging of [piotrhoppe/netbeans-cnd](https://github.com/piotrhoppe/netbeans-cnd) for installation using NetBeans Plugin Manager.

## Status

Source build and update-center packaging pass. Clean NetBeans 31 installation and runtime verification are in progress. **The public update center is not published yet.**

## Intended installation

Once publication is enabled:

1. Open **Tools → Plugins → Settings → Add**.
2. Name: **C/C++ Support**. Paste the published catalog URL.
3. Open **Available Plugins**, refresh, and install **C/C++ Support for NetBeans 31**.
4. Accept the license and restart NetBeans.

The visible feature installs the complete CND module set automatically. These community packages are unsigned; NetBeans may ask you to accept them.

A compiler, Make, and optionally GDB and clangd must be available separately. The plugin is not a compiler. Windows toolchain setup still needs to be documented and verified before describing this as a complete Windows setup for a student.

## Build and verification

CI checks out immutable source revisions:

- CND: `piotrhoppe/netbeans-cnd@d6b3122946815b16b613449723b09cafc3a46036`.
- Yenta: `piotrhoppe/yenta@a962a8bf57d305dd436ab1c1d8a01f47e35a9ad7`.
- Test target: the clean Apache NetBeans 31 binary distribution, with JDK 21.

The workflow builds the dependencies, collects all NBMs, checks bundled Class-Path libraries, and generates a single visible feature plus its catalog and SHA-256 checksums. The installation test uses NetBeans Plugin Manager with the generated local catalog. A test-only module then checks module activation, C/C++ project creation, editing and saving, the IDE Build action, and native execution of the compiled C++ program.

The probe is never included in the published packages. Verification logs and packages are available as workflow artifacts. A compiled NBM alone is not treated as runtime verification.

## Licensing

CND sources retain their upstream Apache 2.0 licensing and notices. Yenta includes legacy Oracle/Sun code under CDDL/GPLv2 with the Classpath exception; see its source headers. No claim of Apache Software Foundation endorsement is made.
