// ==UserScript==
// @name         Gemini Mass Exporter v8.0 - Progressive
// @version      8.0
// @description  Scrolla a lista, abre cada chat, scrolla até o topo e salva um por um.
// @author       Gemini Thought Partner
// @match        https://gemini.google.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const SELECTORS = {
        sidebarScroll: '.chat-history-list, infinite-scroller[data-test-id="history-sidebar-list"]',
        chatScroll: '#chat-history, .chat-history-scroll-container, infinite-scroller[data-test-id="chat-history-container"]',
        convItem: 'div[data-test-id="conversation"], .conversation-item',
        msgText: '.message-content, .model-response-text, .user-query-content, .conversation-turn-content, .query-text, .response-text',
        userContainer: '.user-query, [data-test-id="user-query"], .query-container',
        modelContainer: '.model-response, [data-test-id="model-response"], .response-container',
        loadingSpinner: 'mat-progress-spinner, .loading-indicator, [role="progressbar"]'
    };

    // ⚡ MODO TURBO: Configurações otimizadas para velocidade
    const TURBO_CONFIG = {
        scrollStep: 800,              // 🚀 Sobe mais rápido (era 400)
        scrollDelay: 800,             // 🚀 Delay reduzido (era 2000)
        maxScrollAttempts: 80,        // Limite mais agressivo
        stableCheckCount: 2,          // 🚀 Apenas 2 checks (era 4)
        chatOpenDelay: 2500,          // 🚀 Reduzido (era 5000)
        sidebarLoadDelay: 3000,       // Aumentado significativamente para lazy-loading
        sidebarScrollStep: 9999,      // Scroll até o fim de uma vez
        finalCaptureDelay: 1500,      // 🚀 Reduzido (era 3000)
        skipSidebarReload: false      // Sempre faz scroll completo para garantir todas as conversas
    };

    // 🐌 MODO SAFE: Configurações conservadoras (como v9.2)
    const SAFE_CONFIG = {
        scrollStep: 400,
        scrollDelay: 2000,
        maxScrollAttempts: 150,
        stableCheckCount: 4,
        chatOpenDelay: 5000,
        sidebarLoadDelay: 2500,
        sidebarScrollStep: 800,
        finalCaptureDelay: 3000,
        skipSidebarReload: false
    };

    let CONFIG = TURBO_CONFIG; // 🚀 Padrão é TURBO
    let progressDialog = null;
    let startButton = null;
    let stopButton = null;
    let modeButton = null;
    let isRunning = false;
    let shouldStop = false;
    let isTurboMode = true;
    let sidebarAlreadyLoaded = false;

    // ===== INTERFACE VISUAL =====
    function createUI() {
        // Botão de início
        startButton = document.createElement('button');
        startButton.innerHTML = '⚡ Iniciar TURBO Export v9.3';
        Object.assign(startButton.style, {
            position: 'fixed', top: '10px', left: '50%', transform: 'translateX(-50%)',
            zIndex: '10001', padding: '12px 24px', background: '#ff6b00', color: 'white',
            border: 'none', borderRadius: '25px', cursor: 'pointer', fontWeight: 'bold',
            fontSize: '14px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transition: 'all 0.3s ease'
        });
        startButton.onmouseover = () => startButton.style.background = '#e55d00';
        startButton.onmouseout = () => startButton.style.background = '#ff6b00';
        startButton.onclick = startFullExport;
        document.body.appendChild(startButton);

        // Botão de modo (TURBO/SAFE)
        modeButton = document.createElement('button');
        modeButton.innerHTML = '🐌 Modo: TURBO';
        Object.assign(modeButton.style, {
            position: 'fixed', top: '10px', left: '20px',
            zIndex: '10001', padding: '10px 20px', background: '#6c757d', color: 'white',
            border: 'none', borderRadius: '20px', cursor: 'pointer', fontWeight: 'bold',
            fontSize: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transition: 'all 0.3s ease'
        });
        modeButton.onclick = toggleMode;
        document.body.appendChild(modeButton);

        // Botão de parar
        stopButton = document.createElement('button');
        stopButton.innerHTML = '⏹️ PARAR';
        Object.assign(stopButton.style, {
            position: 'fixed', top: '10px', right: '20px',
            zIndex: '10001', padding: '12px 24px', background: '#dc3545', color: 'white',
            border: 'none', borderRadius: '25px', cursor: 'pointer', fontWeight: 'bold',
            fontSize: '14px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transition: 'all 0.3s ease', display: 'none'
        });
        stopButton.onmouseover = () => stopButton.style.background = '#c82333';
        stopButton.onmouseout = () => stopButton.style.background = '#dc3545';
        stopButton.onclick = stopExport;
        document.body.appendChild(stopButton);

        // Dialog de progresso
        progressDialog = document.createElement('div');
        Object.assign(progressDialog.style, {
            position: 'fixed', top: '70px', left: '50%', transform: 'translateX(-50%)',
            zIndex: '10002', background: 'rgba(0,0,0,0.9)', color: 'white',
            padding: '20px 30px', borderRadius: '15px', fontFamily: 'monospace',
            fontSize: '13px', display: 'none', maxWidth: '600px', minWidth: '400px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)', maxHeight: '80vh', overflow: 'auto'
        });
        document.body.appendChild(progressDialog);
    }

    function toggleMode() {
        if (isRunning) return; // Não permite trocar durante execução

        isTurboMode = !isTurboMode;
        CONFIG = isTurboMode ? TURBO_CONFIG : SAFE_CONFIG;

        if (isTurboMode) {
            modeButton.innerHTML = '⚡ Modo: TURBO';
            modeButton.style.background = '#ff6b00';
            startButton.innerHTML = '⚡ Iniciar TURBO Export v9.3';
            startButton.style.background = '#ff6b00';
        } else {
            modeButton.innerHTML = '🐌 Modo: SAFE';
            modeButton.style.background = '#28a745';
            startButton.innerHTML = '🐌 Iniciar SAFE Export v9.3';
            startButton.style.background = '#28a745';
        }

        console.log(`[v9.3] Modo alterado para: ${isTurboMode ? 'TURBO ⚡' : 'SAFE 🐌'}`);
    }

    function updateProgress(message, isComplete = false) {
        progressDialog.style.display = 'block';
        const mode = isTurboMode ? '⚡ TURBO' : '🐌 SAFE';
        const statusEmoji = isComplete ? '✅' : (shouldStop ? '⏹️' : '⏳');
        const statusText = isComplete ? 'Concluído!' : (shouldStop ? 'Parando...' : 'Processando...');

        progressDialog.innerHTML = `
            <div style="margin-bottom: 10px; font-size: 16px; font-weight: bold;">
                ${statusEmoji} ${statusText} (${mode})
            </div>
            <div style="line-height: 1.6; white-space: pre-wrap;">${message}</div>
        `;
    }

    function stopExport() {
        shouldStop = true;
        stopButton.style.background = '#6c757d';
        stopButton.style.cursor = 'not-allowed';
        stopButton.innerHTML = '⏹️ Parando...';
        updateProgress('⏹️ Cancelamento solicitado...\nAguarde o chat atual finalizar.', false);
    }

    const sleep = ms => new Promise(res => setTimeout(res, ms));

    // ===== FUNÇÕES DE SCROLL =====
    function findScrollContainer(selectors) {
        const selector = Array.isArray(selectors) ? selectors.join(', ') : selectors;
        const elements = document.querySelectorAll(selector);

        console.log(`🔍 Procurando scroll container com: "${selector}"`);
        console.log(`   Encontrados ${elements.length} elementos`);

        for (let i = 0; i < elements.length; i++) {
            const el = elements[i];
            console.log(`   [${i}] scrollHeight: ${el.scrollHeight}, clientHeight: ${el.clientHeight}, class: "${el.className}"`);
            if (el.scrollHeight > el.clientHeight) {
                console.log(`   ✅ Usando elemento [${i}]`);
                return el;
            }
        }

        if (elements[0]) {
            console.log(`   ⚠️ Nenhum com scroll, usando primeiro elemento`);
        } else {
            console.log(`   ❌ Nenhum elemento encontrado!`);
        }
        return elements[0] || null;
    }

    async function scrollSidebarIncrementally() {
        console.log("[v9.3] 📋 Iniciando scroll da SIDEBAR DA LISTA DE CHATS...");
        updateProgress('📋 Carregando conversas da sidebar...');

        const sidebar = findScrollContainer(SELECTORS.sidebarScroll);
        if (!sidebar) {
            console.warn("⚠️ Sidebar não encontrada! Tentando seletores alternativos...");
            // Tenta seletores mais genéricos
            const alternatives = document.querySelectorAll('[class*="sidebar"], [class*="history"], [class*="conversation-list"]');
            console.log(`   Encontrados ${alternatives.length} elementos alternativos:`, alternatives);
            return;
        }

        console.log(`✅ Sidebar encontrada:`, sidebar);
        console.log(`   - scrollHeight inicial: ${sidebar.scrollHeight}px`);
        console.log(`   - clientHeight: ${sidebar.clientHeight}px`);

        let lastHeight = 0;
        let stableCount = 0;
        let maxAttempts = 150;  // Aumentado
        let attempts = 0;

        while (stableCount < 5 && attempts < maxAttempts) {  // 5 tentativas estáveis
            if (shouldStop) break;

            attempts++;
            const beforeHeight = sidebar.scrollHeight;
            const beforeCount = document.querySelectorAll(SELECTORS.convItem).length;

            // SCROLL ATÉ O FIM DE UMA VEZ
            sidebar.scrollTop = sidebar.scrollHeight;

            console.log(`[${attempts}] Scrolled to bottom (${sidebar.scrollTop}px), waiting ${CONFIG.sidebarLoadDelay}ms...`);

            await sleep(CONFIG.sidebarLoadDelay);

            const afterHeight = sidebar.scrollHeight;
            const afterCount = document.querySelectorAll(SELECTORS.convItem).length;

            if (afterHeight === beforeHeight && afterCount === beforeCount) {
                stableCount++;
                console.log(`   ⏸️ Estável ${stableCount}/5 (${afterCount} conversas)`);
            } else {
                stableCount = 0;
                const newConvs = afterCount - beforeCount;
                const heightDiff = afterHeight - beforeHeight;
                console.log(`   ✨ Novas conversas! +${newConvs} conversas, +${heightDiff}px altura`);
            }

            lastHeight = afterHeight;
            const currentCount = document.querySelectorAll(SELECTORS.convItem).length;
            updateProgress(`📋 Carregando conversas da sidebar...\n📊 ${currentCount} encontradas\n🔄 Rodada ${attempts}/${maxAttempts} | Estável: ${stableCount}/5`);
        }

        const finalCount = document.querySelectorAll(SELECTORS.convItem).length;
        console.log(`[v9.3] ✅ Sidebar carregada! (${attempts} tentativas, ${finalCount} conversas)`);
        console.log(`   Total height: ${sidebar.scrollHeight}px`);
    }

    // ===== CAPTURA DE MENSAGENS =====
    function detectMessageRole(element) {
        let current = element;
        for (let i = 0; i < 10; i++) {
            if (!current || !current.parentElement) break;

            const classes = current.className || '';
            const dataTest = current.getAttribute('data-test-id') || '';

            if (classes.includes('user') ||
                classes.includes('query') ||
                dataTest.includes('user') ||
                dataTest.includes('query')) {
                return 'user';
            }

            if (classes.includes('model') ||
                classes.includes('response') ||
                dataTest.includes('model') ||
                dataTest.includes('response')) {
                return 'model';
            }

            current = current.parentElement;
        }

        return 'model';
    }

    function captureVisibleMessages() {
        const allMessageElements = document.querySelectorAll(SELECTORS.msgText);
        const messages = [];

        for (const el of allMessageElements) {
            const text = el.innerText?.trim() || '';
            if (text.length < 3) continue;

            const role = detectMessageRole(el);
            messages.push({ text, role });
        }

        return messages;
    }

    async function scrollChatToTopTurbo() {
        const chatContainer = findScrollContainer(SELECTORS.chatScroll);
        if (!chatContainer) {
            console.warn("Container de chat não encontrado");
            return [];
        }

        console.log("   ⚡ Scroll TURBO ativado!");

        const seenMessages = new Map();
        let stableCount = 0;
        let attempts = 0;
        let lastCaptureCount = 0;

        // 🚀 OTIMIZAÇÃO 1: Scroll inicial grande (vai logo pro topo)
        chatContainer.scrollTop = 0;
        await sleep(CONFIG.scrollDelay);

        while (stableCount < CONFIG.stableCheckCount && attempts < CONFIG.maxScrollAttempts) {
            if (shouldStop) break;

            attempts++;

            // 🚀 OTIMIZAÇÃO 2: Scroll mais agressivo
            const currentScrollTop = chatContainer.scrollTop;
            chatContainer.scrollTop = Math.max(0, currentScrollTop - CONFIG.scrollStep);

            await sleep(CONFIG.scrollDelay);

            // Captura mensagens
            const currentMessages = captureVisibleMessages();
            let newCount = 0;

            for (const msg of currentMessages) {
                const msgKey = `${msg.role}:${msg.text.substring(0, 150)}`;
                if (!seenMessages.has(msgKey)) {
                    seenMessages.set(msgKey, msg);
                    newCount++;
                }
            }

            // 🚀 OTIMIZAÇÃO 3: Detecção mais rápida do topo
            if (chatContainer.scrollTop === 0) {
                if (seenMessages.size === lastCaptureCount) {
                    stableCount++;
                } else {
                    stableCount = 0;
                    lastCaptureCount = seenMessages.size;
                }
            } else {
                stableCount = 0;
            }

            // 🚀 OTIMIZAÇÃO 4: Não espera spinner em modo TURBO
            if (!isTurboMode) {
                const spinner = document.querySelector(SELECTORS.loadingSpinner);
                if (spinner && spinner.offsetParent !== null) {
                    await sleep(CONFIG.scrollDelay);
                    stableCount = 0;
                }
            }

            // Log apenas a cada 10 tentativas
            if (attempts % 10 === 0) {
                console.log(`      [${attempts}] ${seenMessages.size} msgs`);
            }
        }

        // Captura final reduzida
        await sleep(CONFIG.finalCaptureDelay);
        const finalMessages = captureVisibleMessages();

        for (const msg of finalMessages) {
            const msgKey = `${msg.role}:${msg.text.substring(0, 150)}`;
            if (!seenMessages.has(msgKey)) {
                seenMessages.set(msgKey, msg);
            }
        }

        const allMessages = Array.from(seenMessages.values());
        const userMsgs = allMessages.filter(m => m.role === 'user');
        const modelMsgs = allMessages.filter(m => m.role === 'model');

        console.log(`   ✅ ${userMsgs.length} user + ${modelMsgs.length} model = ${allMessages.length} total`);

        return allMessages;
    }

    // ===== PROCESSO PRINCIPAL =====
    async function startFullExport() {
        if (isRunning) return;

        isRunning = true;
        shouldStop = false;
        startButton.style.display = 'none';
        stopButton.style.display = 'block';
        modeButton.style.display = 'none'; // Esconde durante execução

        const startTime = Date.now();

        try {
            await scrollSidebarIncrementally();

            if (shouldStop) {
                finishExport(true, 0, 0, 0, startTime);
                return;
            }

            console.log(`[v9.3] 🔍 Buscando conversas com seletor: "${SELECTORS.convItem}"`);
            const conversations = Array.from(document.querySelectorAll(SELECTORS.convItem));
            console.log(`[v9.3] 📊 ${conversations.length} conversas encontradas`);

            if (conversations.length === 0) {
                console.error("❌ NENHUMA conversa encontrada com o seletor atual!");
                console.log("   Tentando seletores alternativos...");

                // Tenta encontrar elementos que possam ser conversas
                const alternatives = [
                    'div[class*="conversation"]',
                    'div[class*="chat"]',
                    'button[class*="conversation"]',
                    'a[class*="conversation"]',
                    '[data-test-id*="conversation"]',
                    '[data-test-id*="chat"]'
                ];

                for (const alt of alternatives) {
                    const found = document.querySelectorAll(alt);
                    if (found.length > 0) {
                        console.log(`   ✅ "${alt}" encontrou ${found.length} elementos`);
                        console.log(`      Exemplo:`, found[0]);
                    }
                }

                alert("⚠️ Nenhuma conversa encontrada! Veja o console (F12) para debug.");
                finishExport(true, 0, 0, 0, startTime);
                return;
            }

            console.log(`   Primeiras 3 conversas:`, conversations.slice(0, 3).map(c => c.innerText?.split('\n')[0]));

            let exportedCount = 0;
            let warningCount = 0;
            let lastSidebarScroll = 0;

            for (let i = 0; i < conversations.length; i++) {
                if (shouldStop) {
                    console.log(`[v9.3] ⏹️ Cancelado após ${exportedCount} chats`);
                    break;
                }

                // 🔄 A cada 5 chats, tenta carregar mais conversas na sidebar
                if (i > 0 && i % 5 === 0) {
                    console.log(`[v9.3] 🔄 Checando se há mais conversas na sidebar...`);
                    const sidebar = findScrollContainer(SELECTORS.sidebarScroll);
                    if (sidebar) {
                        let scrollAttempts = 0;
                        let totalNewConvs = 0;

                        // Continua scrollando até não carregar mais nada (máx 10 tentativas)
                        while (scrollAttempts < 10) {
                            const beforeCount = document.querySelectorAll(SELECTORS.convItem).length;
                            sidebar.scrollTop = sidebar.scrollHeight;
                            await sleep(CONFIG.sidebarLoadDelay);
                            const afterCount = document.querySelectorAll(SELECTORS.convItem).length;

                            if (afterCount > beforeCount) {
                                const newConvs = Array.from(document.querySelectorAll(SELECTORS.convItem));
                                // Adiciona novas conversas ao array
                                for (let j = conversations.length; j < newConvs.length; j++) {
                                    conversations.push(newConvs[j]);
                                }
                                const newCount = afterCount - beforeCount;
                                totalNewConvs += newCount;
                                console.log(`   ✨ +${newCount} conversas (total: ${afterCount})`);
                                scrollAttempts = 0; // Reset counter se encontrou novas
                            } else {
                                scrollAttempts++;
                            }
                        }

                        if (totalNewConvs > 0) {
                            console.log(`   🎉 Carregadas ${totalNewConvs} conversas novas! Continuando exportação...`);
                        }
                    }
                }

                const conv = conversations[i];
                let title = conv.innerText?.trim().split('\n')[0] || `Conversa_${i+1}`;
                title = title.replace(/[/\\?%*:|"<>]/g, '-').substring(0, 100);

                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                const avgTime = exportedCount > 0 ? (elapsed / exportedCount).toFixed(1) : '?';
                const remaining = exportedCount > 0 ?
                    (((conversations.length - i) * avgTime) / 60).toFixed(1) : '?';

                updateProgress(
                    `📂 Chat ${i+1}/${conversations.length}\n` +
                    `🔍 "${title}"\n\n` +
                    `⏱️ ${elapsed}s | Média: ${avgTime}s/chat\n` +
                    `⏳ ~${remaining} min restantes\n` +
                    `✅ Exportados: ${exportedCount}`
                );

                console.log(`[${i+1}/${conversations.length}] ${title}`);

                conv.click();
                await sleep(CONFIG.chatOpenDelay);

                const messages = await scrollChatToTopTurbo();

                if (messages.length === 0) {
                    console.error(`   ❌ Nenhuma mensagem!`);
                    warningCount++;
                } else if (messages.length === 1) {
                    console.warn(`   ⚠️ Só 1 mensagem`);
                    warningCount++;
                }

                const chatData = {
                    numero: i + 1,
                    titulo: title,
                    url: window.location.href,
                    total_mensagens: messages.length,
                    mensagens: messages,
                    exportado_em: new Date().toISOString(),
                    debug_info: {
                        user_messages: messages.filter(m => m.role === 'user').length,
                        model_messages: messages.filter(m => m.role === 'model').length,
                        mode: isTurboMode ? 'TURBO' : 'SAFE'
                    }
                };

                saveIndividualFile(chatData, i + 1, conversations.length);
                exportedCount++;

                await sleep(500); // Pequena pausa entre chats
            }

            finishExport(false, exportedCount, conversations.length, warningCount, startTime);

        } catch (error) {
            console.error("[v9.3] ❌ Erro:", error);
            alert(`❌ Erro: ${error.message}\n\nF12 para detalhes.`);
            finishExport(true, 0, 0, 0, startTime);
        }
    }

    function saveIndividualFile(chatData, chatNumber, totalChats) {
        const timestamp = new Date().toISOString().split('T')[0];
        const cleanTitle = chatData.titulo.substring(0, 50).replace(/[/\\?%*:|"<>]/g, '-');
        const filename = `Gemini_Chat_${String(chatNumber).padStart(3, '0')}_${cleanTitle}_${timestamp}.json`;

        const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function finishExport(wasCancelled, exportedCount, totalCount, warningCount, startTime) {
        isRunning = false;
        startButton.style.display = 'block';
        stopButton.style.display = 'none';
        modeButton.style.display = 'block';
        stopButton.style.background = '#dc3545';
        stopButton.style.cursor = 'pointer';
        stopButton.innerHTML = '⏹️ PARAR';

        const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
        const avgTime = exportedCount > 0 ? (totalTime / exportedCount).toFixed(1) : 0;

        let message = '';

        if (wasCancelled) {
            message = `⏹️ Exportação Cancelada!\n\n` +
                     `✅ Exportados: ${exportedCount} de ${totalCount}\n` +
                     `⏱️ Tempo total: ${totalTime}s`;
        } else {
            message = `✅ Exportação Completa!\n\n` +
                     `📊 Total: ${exportedCount} chats\n` +
                     `⏱️ Tempo total: ${totalTime}s (${avgTime}s/chat)\n` +
                     `📁 Arquivos na pasta Downloads`;

            if (warningCount > 0) {
                message += `\n\n⚠️ ${warningCount} avisos (F12 para detalhes)`;
            }
        }

        updateProgress(message, true);

        setTimeout(() => {
            progressDialog.style.display = 'none';
        }, 15000);
    }

    // ===== INICIALIZAÇÃO =====
    setTimeout(createUI, 2000);
    console.log("[v9.3] 🚀 Gemini Mass Exporter v9.3 TURBO carregado!");
    console.log("[v9.3] ⚡ Modo TURBO ativo por padrão (clique no botão para trocar)");
})();
