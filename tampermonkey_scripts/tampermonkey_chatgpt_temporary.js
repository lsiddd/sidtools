// ==UserScript==
// @name         ChatGPT Temporary Chat Enforcer
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automatically adds temporary-chat=true parameter to ChatGPT URLs
// @author       You
// @match        https://chatgpt.com/*
// @match        https://*.chatgpt.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Create a URL object to parse the current URL
    const currentUrl = new URL(window.location.href);

    // Check if the temporary-chat parameter is missing
    if (!currentUrl.searchParams.has('temporary-chat')) {
        // Add the temporary-chat parameter
        currentUrl.searchParams.set('temporary-chat', 'true');

        // Replace the current URL with the modified version
        window.location.replace(currentUrl.href);
    }
})();
