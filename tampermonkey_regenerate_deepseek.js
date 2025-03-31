// ==UserScript==
// @name         Auto Regenerate DeepSeek
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Automatiza o clique no botão "Regenerate" ao detectar a mensagem de erro "The server is busy. Please try again later."
// @author       Você
// @match        https://chat.deepseek.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Função para verificar a presença da mensagem de erro e clicar no botão "Regenerate"
    function checkAndRegenerate() {
        // Texto da mensagem de  erro
        const errorMessageText = 'The server is busy. Please try again later.';
        // ID do botão "Regenerate"
        const regenerateButtonId = '重新生成'; // Substitua pelo ID correto

        // Encontre a mensagem de erro pelo texto
        const errorMessageElement = Array.from(document.body.getElementsByTagName('*'))
            .find(element => element.textContent.trim() === errorMessageText);

        // Se a mensagem de erro estiver presente
        if (errorMessageElement) {
            // Encontre o botão "Regenerate" pelo ID
            const regenerateButton = document.getElementById(regenerateButtonId);

            // Se o botão "Regenerate" for encontrado
            if (regenerateButton) {
                // Tentar disparar o evento de clique diretamente
                const event = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });

                regenerateButton.dispatchEvent(event); // Dispara o evento de clique
                console.log('Botão "Regenerate" clicado.');
            } else {
                console.error('Botão "Regenerate" não encontrado.');
            }
        } else {
            console.log('Mensagem de erro não encontrada.');
        }
    }

    // Defina um intervalo para verificar a cada 5 segundos
    setInterval(checkAndRegenerate, 5000);
})();
