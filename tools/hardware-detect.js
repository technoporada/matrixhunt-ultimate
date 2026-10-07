/**
 * MATRIXHUNT ULTIMATE - Hardware Detection Engine
 * License: CC BY-NC-SA 4.0
 * Author: Arkadiusz Slowik
 *
 * Pure browser-based detection: WebGL, Gamepad API, Screen, Navigator
 * No plugins, no applets, no installation required.
 * Works like "Can You Run It" but for emulators, and WITHOUT plugins.
 */

class HardwareDetector {
    constructor() {
        this.results = null;
    }

    /**
     * Run full hardware scan
     * @returns {Object} Complete hardware info
     */
    async detectAll() {
        this.results = {
            gpu: this.detectGPU(),
            cpu: this.detectCPU(),
            ram: this.detectRAM(),
            display: await this.detectDisplay(),
            controller: await this.detectController(),
            vulkan: await this.detectVulkan(),
            browser: this.detectBrowser(),
            os: this.detectOS(),
            battery: await this.detectBattery(),
            timestamp: new Date().toISOString()
        };
        return this.results;
    }

    /**
     * Detect GPU via WebGL debug renderer info
     */
    detectGPU() {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;

        let gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
        if (!gl) {
            return { vendor: 'Unknown', renderer: 'WebGL not supported', score: 0, supportsWebGL2: false };
        }

        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        let vendor = 'Unknown';
        let renderer = 'Unknown';

        if (debugInfo) {
            vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL || gl.VENDOR);
            renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL || gl.RENDERER);
        } else {
            vendor = gl.getParameter(gl.VENDOR);
            renderer = gl.getParameter(gl.RENDERER);
        }

        const supportsWebGL2 = !!canvas.getContext('webgl2');

        return {
            vendor: vendor,
            renderer: renderer,
            score: getGPUScore(renderer),
            supportsWebGL2: supportsWebGL2
        };
    }

    /**
     * Detect CPU cores via navigator.hardwareConcurrency
     */
    detectCPU() {
        const cores = navigator.hardwareConcurrency || 0;
        let tier = 'unknown';
        if (cores >= 16) tier = 'excellent';
        else if (cores >= 8) tier = 'good';
        else if (cores >= 6) tier = 'ok';
        else if (cores >= 4) tier = 'fair';
        else if (cores >= 2) tier = 'weak';
        else tier = 'very-weak';

        return { cores: cores, tier: tier };
    }

    /**
     * Detect RAM via navigator.deviceMemory (Chrome/Edge only)
     */
    detectRAM() {
        const gb = navigator.deviceMemory || 0;
        let tier = 'unknown';
        if (gb >= 32) tier = 'excellent';
        else if (gb >= 16) tier = 'good';
        else if (gb >= 8) tier = 'ok';
        else if (gb >= 4) tier = 'fair';
        else if (gb >= 2) tier = 'weak';
        else tier = 'very-weak';

        return { gb: gb, tier: tier, available: gb > 0 };
    }

    /**
     * Measure display refresh rate by sampling requestAnimationFrame deltas.
     * Browsers do not expose the true refresh rate, so we infer it from the
     * median frame interval over a short burst of frames.
     * @returns {Promise<number|null>} Rounded Hz, or null when unmeasurable.
     */
    measureRefreshRate(frames = 30) {
        return new Promise(resolve => {
            if (typeof requestAnimationFrame !== 'function') {
                resolve(null);
                return;
            }

            const deltas = [];
            let last = null;
            let rafId = null;
            let done = false;

            const finish = () => {
                if (done) return;
                done = true;
                if (rafId !== null) cancelAnimationFrame(rafId);
                if (deltas.length < 2) {
                    resolve(null);
                    return;
                }
                deltas.sort((a, b) => a - b);
                const median = deltas[Math.floor(deltas.length / 2)];
                if (!(median > 0)) {
                    resolve(null);
                    return;
                }
                resolve(Math.round(1000 / median));
            };

            const tick = (now) => {
                if (last !== null) {
                    deltas.push(now - last);
                    if (deltas.length >= frames) {
                        finish();
                        return;
                    }
                }
                last = now;
                rafId = requestAnimationFrame(tick);
            };

            rafId = requestAnimationFrame(tick);
            // Bail out on background tabs / throttled rAF.
            setTimeout(finish, 2000);
        });
    }

    /**
     * Detect display properties
     */
    async detectDisplay() {
        const estimatedHz = await this.measureRefreshRate();

        return {
            width: screen.width,
            height: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
            colorDepth: screen.colorDepth,
            pixelRatio: window.devicePixelRatio || 1,
            estimatedHz: estimatedHz,
            isRetina: (window.devicePixelRatio || 1) >= 2
        };
    }

    /**
     * Detect connected gamepads via Gamepad API
     */
    async detectController() {
        // The Gamepad API snapshot is empty until the user presses a button,
        // and the page's whole job is finding controllers, so a first scan
        // always said "None detected". Wait briefly for gamepadconnected.
        let gamepads = [];
        const read = () => {
            try {
                if (navigator.getGamepads) {
                    return Array.from(navigator.getGamepads()).filter(Boolean);
                }
            } catch (e) { /* not supported */ }
            return [];
        };
        gamepads = read();
        if (!gamepads.length && typeof window !== 'undefined'
            && typeof window.addEventListener === 'function') {
            gamepads = await new Promise((resolve) => {
                let done = false;
                const finish = () => {
                    if (done) return;
                    done = true;
                    window.removeEventListener('gamepadconnected', finish);
                    resolve(read());
                };
                window.addEventListener('gamepadconnected', finish);
                // Short grace period, then report honestly.
                setTimeout(finish, 1200);
            });
        }

        const controllers = gamepads.map(gp => ({
            id: gp.id || 'Unknown',
            index: gp.index,
            axes: gp.axes ? gp.axes.length : 0,
            buttons: gp.buttons ? gp.buttons.length : 0,
            mapping: gp.mapping || 'standard',
            connected: gp.connected !== false,
            timestamp: gp.timestamp || 0
        }));

        // Try to identify controller type
        const identified = controllers.map(c => {
            let type = 'Unknown';
            const id = c.id.toLowerCase();
            if (id.includes('xbox') || id.includes('xinput') || id.includes('microsoft')) type = 'Xbox';
            else if (id.includes('playstation') || id.includes('sony') || id.includes('dualshock') || id.includes('dualsense')) type = 'PlayStation';
            else if (id.includes('nintendo') || id.includes('switch') || id.includes('pro controller')) type = 'Switch Pro';
            else if (id.includes('8bitdo')) type = '8BitDo';
            else if (id.includes('logitech')) type = 'Logitech';
            else if (c.mapping === 'standard') type = 'Standard (XInput)';

            return { ...c, type: type };
        });

        return {
            connected: identified.length > 0,
            count: identified.length,
            controllers: identified
        };
    }

    /**
     * Detect Vulkan support via WebGPU API (indirect indicator)
     */
    async detectVulkan() {
        // WebGPU is the closest browser API to Vulkan detection
        let webgpu = false;
        try {
            if (navigator.gpu) {
                const adapter = await navigator.gpu.requestAdapter();
                webgpu = !!adapter;
            }
        } catch (e) {
            webgpu = false;
        }

        // WebGL2 has nothing to do with Vulkan. `supported: webgpu || webgl2`
        // handed every machine with WebGL2 the Vulkan bonus and dodged the
        // missing-Vulkan penalty, and the UI printed "Vulkan: YES". Browsers
        // cannot detect Vulkan at all, so the only honest signal is WebGPU.
        const canvas = document.createElement('canvas');
        const webgl2 = !!canvas.getContext('webgl2');

        return {
            webgpu: webgpu,
            webgl2: webgl2,
            supported: webgpu,
            // True when we genuinely cannot know, so the scorer can say
            // "unknown" instead of quietly assuming the best or worst case.
            unknown: !webgpu,
            note: 'Vulkan is not detectable from a browser; WebGPU is used as the proxy signal.'
        };
    }

    /**
     * Detect browser info
     */
    detectBrowser() {
        const ua = navigator.userAgent;
        let name = 'Unknown';
        let version = 'Unknown';

        // Chromium forks first: they all send Chrome/ in the UA, so testing
        // Chrome/ before them reported Opera, Samsung Internet and Vivaldi
        // as "Chrome" and left the Opera branch unreachable.
        if (ua.includes('OPR/') || ua.includes('Opera')) {
            name = 'Opera';
            version = ua.split('OPR/')[1]?.split(' ')[0] || ua.split('Opera/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('SamsungBrowser')) {
            name = 'Samsung Internet';
            version = ua.split('SamsungBrowser/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('Vivaldi/')) {
            name = 'Vivaldi';
            version = ua.split('Vivaldi/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('YaBrowser')) {
            name = 'Yandex';
            version = ua.split('YaBrowser/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('CriOS')) {
            name = 'Chrome iOS';
            version = ua.split('CriOS/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('FxiOS')) {
            name = 'Firefox iOS';
            version = ua.split('FxiOS/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('Edg/')) {
            name = 'Edge';
            version = ua.split('Edg/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('Firefox/') || ua.includes('FxiOS')) {
            name = 'Firefox';
            version = ua.split('Firefox/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('Chrome/') || ua.includes('Chromium/')) {
            name = 'Chrome';
            version = ua.split('Chrome/')[1]?.split(' ')[0] || 'Unknown';
        } else if (ua.includes('Safari/') && ua.includes('Version/')) {
            name = 'Safari';
            version = ua.split('Version/')[1]?.split(' ')[0] || 'Unknown';
        }

        const isBrave = navigator.brave && navigator.brave.isBrave;
        if (isBrave) {
            name = 'Brave';
        }

        return { name: name, version: version, userAgent: ua };
    }

    /**
     * Detect OS
     */
    detectOS() {
        const ua = navigator.userAgent;
        let name = 'Unknown';
        let arch = 'Unknown';

        // Order matters and the order was wrong: Android UAs contain
        // "(Linux; Android 13; ...)" and iOS UAs contain "like Mac OS X",
        // so testing Mac/Linux first reported every phone as a desktop.
        if (ua.includes('Windows NT 10.0')) name = 'Windows 10/11';
        else if (ua.includes('Windows NT 6.3')) name = 'Windows 8.1';
        else if (ua.includes('Windows NT 6.2')) name = 'Windows 8';
        else if (ua.includes('Windows NT 6.1')) name = 'Windows 7';
        else if (ua.includes('Windows')) name = 'Windows';
        else if (ua.includes('Android')) name = 'Android';
        else if (/iPhone|iPad|iPod/.test(ua)) name = 'iOS';
        else if (ua.includes('CrOS')) name = 'ChromeOS';
        else if (ua.includes('Mac OS X')) name = 'macOS';
        else if (ua.includes('Linux')) name = 'Linux';

        if (ua.includes('x64') || ua.includes('x86_64') || ua.includes('Win64') || ua.includes('WOW64')) arch = 'x64';
        else if (ua.includes('arm64') || ua.includes('aarch64')) arch = 'arm64';
        else if (ua.includes('arm') || ua.includes('armv7')) arch = 'arm32';
        else arch = 'x86';

        return { name: name, arch: arch };
    }

    /**
     * Detect battery status
     */
    async detectBattery() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                return {
                    available: true,
                    charging: battery.charging,
                    level: Math.round(battery.level * 100),
                    chargingTime: battery.chargingTime === Infinity ? 'unknown' : battery.chargingTime,
                    dischargingTime: battery.dischargingTime === Infinity ? 'unknown' : battery.dischargingTime
                };
            }
        } catch (e) {
            // Battery API not supported or permission denied
        }
        return { available: false };
    }
}

/**
 * Render hardware summary to a DOM element
 */
function renderHardwareSummary(hw, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const gpuColor = hw.gpu.score >= 60 ? 'var(--ok)' : hw.gpu.score >= 30 ? 'var(--mid)' : 'var(--bad)';
    const cpuColor = hw.cpu.cores >= 6 ? 'var(--ok)' : hw.cpu.cores >= 4 ? 'var(--mid)' : 'var(--bad)';
    const ramColor = hw.ram.gb >= 8 ? 'var(--ok)' : hw.ram.gb >= 4 ? 'var(--mid)' : 'var(--bad)';
    const vulkanColor = hw.vulkan.supported ? 'var(--ok)' : 'var(--bad)';

    let controllerHTML = '<span style="color:var(--bad);">None detected</span>';
    if (hw.controller.connected) {
        const names = hw.controller.controllers.map(c => c.type).join(', ');
        controllerHTML = '<span style="color:var(--ok);">' + hw.controller.count + ' connected (' + names + ')</span>';
    }

    el.innerHTML =
        '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:0.85em;">' +
            '<div><span style="opacity:0.5;">GPU:</span> <span style="color:' + gpuColor + ';">' + hw.gpu.renderer + '</span> <span style="opacity:0.5;">[score: ' + hw.gpu.score + ']</span></div>' +
            '<div><span style="opacity:0.5;">CPU:</span> <span style="color:' + cpuColor + ';">' + hw.cpu.cores + ' cores</span> <span style="opacity:0.5;">[' + hw.cpu.tier + ']</span></div>' +
            '<div><span style="opacity:0.5;">RAM:</span> <span style="color:' + ramColor + ';">' + (hw.ram.gb > 0 ? hw.ram.gb + ' GB' : 'Unknown') + '</span></div>' +
            '<div><span style="opacity:0.5;">Display:</span> <span style="color:var(--green);">' + hw.display.width + 'x' + hw.display.height + ' @ ' + hw.display.pixelRatio + 'x DPR</span> <span style="opacity:0.5;">[' + (hw.display.estimatedHz ? hw.display.estimatedHz + ' Hz' : 'Hz unknown') + ']</span></div>' +
            '<div><span style="opacity:0.5;">Controller:</span> ' + controllerHTML + '</div>' +
            '<div><span style="opacity:0.5;">Vulkan/WebGPU:</span> <span style="color:' + vulkanColor + ';">' + (hw.vulkan.supported ? 'YES' : 'NO') + '</span></div>' +
            '<div><span style="opacity:0.5;">Browser:</span> <span style="color:var(--green);">' + hw.browser.name + ' ' + hw.browser.version + '</span></div>' +
            '<div><span style="opacity:0.5;">OS:</span> <span style="color:var(--green);">' + hw.os.name + ' ' + hw.os.arch + '</span></div>' +
            (hw.battery.available ?
                '<div><span style="opacity:0.5;">Battery:</span> <span style="color:' + (hw.battery.charging ? 'var(--ok)' : 'var(--warn)') + ';">' + hw.battery.level + '% ' + (hw.battery.charging ? '(charging)' : '') + '</span></div>' : '') +
        '</div>';
}

/**
 * Render compatibility matrix to a DOM element
 */
function renderCompatibilityMatrix(hw, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    // Group by tier
    const tiers = {};
    for (const [key, emu] of Object.entries(EMULATOR_DB)) {
        if (!tiers[emu.tier]) tiers[emu.tier] = [];
        const score = scoreEmulator(emu, hw);
        tiers[emu.tier].push({ key, emu, score });
    }

    const tierOrder = ['retro', 'light', 'medium', 'high', 'ultra', 'experimental'];
    let html = '';

    for (const tier of tierOrder) {
        if (!tiers[tier]) continue;
        const items = tiers[tier].sort((a, b) => b.score - a.score);

        html += '<div style="margin:15px 0 8px; padding:4px 8px; border-bottom:1px solid rgba(0,255,0,0.3);">';
        html += '<span style="font-size:0.75em; letter-spacing:2px; opacity:0.6;">' + getTierLabel(tier) + '</span>';
        html += '</div>';

        for (const item of items) {
            const status = getScoreStatus(item.score);
            const barWidth = Math.max(item.score, 2);
            html += '<div style="display:flex; align-items:center; gap:8px; margin:4px 0; padding:4px 8px;">';
            html += '<span style="width:130px; font-size:0.85em; color:var(--green); flex-shrink:0;">' + item.emu.name + '</span>';
            html += '<div style="flex:1; background:#001100; height:18px; border:1px solid rgba(0,255,0,0.3); overflow:hidden;">';
            html += '<div style="width:' + barWidth + '%; height:100%; background:' + status.color + '; transition:width 0.8s ease;"></div>';
            html += '</div>';
            html += '<span style="width:40px; text-align:right; color:' + status.color + '; font-size:0.85em; font-weight:bold;">' + item.score + '%</span>';
            html += '<span style="width:110px; font-size:0.7em; letter-spacing:1px; color:' + status.color + ';">' + status.text + '</span>';
            html += '</div>';

            if (item.emu.note) {
                html += '<div style="margin-left:140px; font-size:0.7em; opacity:0.5; margin-bottom:4px;">Note: ' + item.emu.note + '</div>';
            }
        }
    }

    el.innerHTML = html;
}

/**
 * Render recommended profile based on detected hardware
 */
function renderRecommendedProfile(hw, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    // Determine best renderer
    let renderer = 'OpenGL';
    if (hw.vulkan.supported) renderer = 'Vulkan';

    // Determine resolution based on GPU score
    let resolution = '1x native';
    if (hw.gpu.score >= 80) resolution = '4x native + AA';
    else if (hw.gpu.score >= 60) resolution = '2x native';
    else if (hw.gpu.score >= 40) resolution = '1.5x native';

    // Determine shader quality
    let shaders = 'none';
    if (hw.gpu.score >= 50) shaders = 'CRT-Royale (retro games)';
    else if (hw.gpu.score >= 30) shaders = 'CRT-Simple (retro games)';

    // Determine VSync
    let vsync = 'OFF';
    if (hw.battery.available && !hw.battery.charging) vsync = 'OFF (battery saving)';
    else if (hw.display.pixelRatio <= 1) vsync = 'ON';

    // Determine run-ahead
    let runAhead = 'OFF';
    if (hw.cpu.cores >= 8 && hw.gpu.score >= 60) runAhead = '2 frames (fighting games)';
    else if (hw.cpu.cores >= 6) runAhead = '1 frame';

    let html = '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:0.85em;">';
    html += '<div><span style="opacity:0.5;">Renderer:</span> <span style="color:var(--green);">' + renderer + '</span></div>';
    html += '<div><span style="opacity:0.5;">Resolution:</span> <span style="color:var(--green);">' + resolution + '</span></div>';
    html += '<div><span style="opacity:0.5;">Shaders:</span> <span style="color:var(--green);">' + shaders + '</span></div>';
    html += '<div><span style="opacity:0.5;">VSync:</span> <span style="color:var(--green);">' + vsync + '</span></div>';
    html += '<div><span style="opacity:0.5;">Run-ahead:</span> <span style="color:var(--green);">' + runAhead + '</span></div>';
    html += '<div><span style="opacity:0.5;">Audio:</span> <span style="color:var(--green);">XAudio2 / cubeb</span></div>';
    html += '</div>';
    html += '<div style="margin-top:12px; font-size:0.75em; opacity:0.5;">These settings are auto-recommended based on your hardware. Apply manually in each emulator.</div>';

    el.innerHTML = html;
}

/**
 * Render preset profiles with scores for current hardware
 */
function renderPresetProfiles(hw, containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    let html = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:10px;">';

    for (const [key, preset] of Object.entries(PRESET_PROFILES)) {
        const isMatch = (
            Math.abs(preset.hw.gpuScore - hw.gpu.score) < 15 &&
            Math.abs(preset.hw.cpuCores - hw.cpu.cores) <= 2 &&
            Math.abs(preset.hw.ramGB - hw.ram.gb) <= 8
        );

        const borderColor = isMatch ? 'var(--ok)' : 'var(--border)';
        const bgColor = isMatch ? 'rgba(0,40,0,0.9)' : 'rgba(0,20,0,0.85)';

        html += '<div style="border:1px solid ' + borderColor + '; background:' + bgColor + '; padding:12px;">';
        html += '<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">';
        html += '<span style="width:30px; height:30px; border:1px solid #0f0; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:0.9em;">' + preset.icon + '</span>';
        html += '<div>';
        html += '<div style="font-size:0.9em; font-weight:bold; letter-spacing:1px;">' + preset.name + '</div>';
        html += '<div style="font-size:0.7em; opacity:0.6;">' + preset.desc + '</div>';
        html += '</div>';
        if (isMatch) {
            html += '<span style="margin-left:auto; font-size:0.65em; color:var(--ok); border:1px solid var(--ok); padding:2px 6px; letter-spacing:1px;">CLOSEST MATCH</span>';
        }
        html += '</div>';

        // Score this preset and the current machine on the same scale. These
        // were computed and then never rendered, so the row showed two raw
        // GPU numbers with nothing to compare them. Now they say which is
        // stronger and by how much.
        const probe = { tier: 'medium', vulkan: true };
        const presetScore = scoreEmulator(probe, preset.hw);
        const currentScore = scoreEmulator(probe, hw);
        const delta = currentScore - presetScore;
        const verdict = delta > 5
            ? '<span style="color:var(--ok);">your machine is stronger (+' + delta + ')</span>'
            : delta < -5
                ? '<span style="color:var(--warn);">preset is stronger (' + delta + ')</span>'
                : '<span style="opacity:0.6;">roughly equal</span>';

        html += '<div style="font-size:0.75em; opacity:0.7;">Preset GPU: '
            + preset.hw.gpuScore + '/100 | Your GPU: ' + hw.gpu.score + '/100</div>';
        html += '<div style="font-size:0.72em; margin-top:3px;">Overall: ' + verdict + '</div>';
        html += '</div>';
    }

    html += '</div>';
    el.innerHTML = html;
}
