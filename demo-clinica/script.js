/* ==========================================================================
   NeuroAssist — demonstração de secretária virtual
   --------------------------------------------------------------------------
   Esta versão NÃO se conecta a nenhuma inteligência artificial.
   As respostas são pré-definidas, exibidas com o selo "Resposta simulada".

   Integração futura com o assistente executado no Strata:
   1. Configure NEURO_ASSIST_CONFIG.demoMode = false
   2. Informe um endpoint HTTPS acessível pelo navegador (proxy/backend)
   3. O backend conversa com o Qwen/Strata e devolve JSON: { "reply": "..." }
   Nunca coloque IP interno, porta, API key ou token neste arquivo.
   ========================================================================== */
'use strict';

/* --------------------------------------------------------------------------
   1. Configuração
   -------------------------------------------------------------------------- */
const NEURO_ASSIST_CONFIG = {
    /**
     * true  -> respostas demonstrativas locais (padrão desta entrega)
     * false -> envia a conversa para apiEndpoint via fetch()
     */
    demoMode: true,

    /** Exemplo futuro: 'https://atendimento.seudominio.com.br/api/chat' */
    apiEndpoint: '',

    /** Tempo máximo de espera pela resposta do backend */
    requestTimeoutMs: 20000,

    /** Quantidade de mensagens enviadas como contexto ao backend */
    maxHistoryMessages: 20,

    /** Limite de caracteres por mensagem (igual ao maxlength do HTML) */
    maxMessageLength: 800,

    /** Faixa de tempo do indicador de digitação na simulação (ms) */
    simulatedTypingDelay: { min: 800, max: 1500 }
};

/* --------------------------------------------------------------------------
   2. Conteúdo demonstrativo
   -------------------------------------------------------------------------- */
const WELCOME_MESSAGE =
    'Olá! Seja bem-vindo(a). Sou a assistente virtual da nossa clínica de neurocirurgia. ' +
    'Estou aqui para ajudar com informações sobre consultas, nossa equipe médica, exames e agendamentos. ' +
    'Como posso ajudar?';

/**
 * Respostas de demonstração. A ordem importa:
 * emergência e assuntos clínicos têm prioridade sobre temas administrativos.
 */
const DEMO_RULES = [
    {
        id: 'emergency',
        pattern: /emergencia|urgente|urgencia|samu|pronto.?socorro|avc|derrame|convuls|desmaio|sangramento|acidente/,
        reply:
            'Este canal não está preparado para urgências.\n\n' +
            'Em caso de emergência ou sintomas neurológicos agudos, procure imediatamente um pronto-socorro ' +
            'ou ligue para o SAMU (192). Não aguarde resposta por aqui.'
    },
    {
        id: 'clinical',
        pattern: /sintoma|dor(es)?\b|diagnostico|remedio|medicacao|medicament|posso tomar|receita|tratamento|pos.?operatorio|formigamento|tontura|resultado do exame|laudo do exame|interpreta/,
        reply:
            'Entendo a sua preocupação, e é importante que você seja avaliado(a) por um médico.\n\n' +
            'Como assistente administrativa, não posso avaliar sintomas, interpretar exames, indicar medicamentos ' +
            'ou sugerir tratamentos. Essas orientações dependem de uma consulta.\n\n' +
            'Posso ajudar a agendar uma avaliação com a nossa equipe de neurocirurgia ou encaminhar seu pedido ' +
            'à secretaria da clínica.'
    },
    {
        id: 'pricing',
        pattern: /valor|preco|quanto custa|custo|pagamento|parcel/,
        reply:
            'Os valores variam conforme o procedimento, o convênio e a forma de atendimento.\n\n' +
            'A secretaria da clínica informa os valores atualizados e verifica a cobertura do seu plano. No ' +
            'atendimento particular, também posso explicar como funciona a solicitação de reembolso, quando aplicável.'
    },
    {
        id: 'location',
        pattern: /localiza|endereco|onde fica|como chegar|estacionamento|horario de funcionamento|horario de atendimento|funcionamento/,
        reply:
            'O atendimento presencial acontece na clínica, com secretaria disponível em dias úteis.\n\n' +
            'Nesta demonstração, o endereço completo, o mapa e o horário oficial de funcionamento ainda não estão ' +
            'cadastrados. Na versão final, essas informações aparecerão aqui e poderão ser enviadas junto com a ' +
            'confirmação do agendamento.\n\n' +
            'Se preferir, posso registrar o seu contato para que a secretaria retorne com os detalhes de acesso ' +
            'e estacionamento.'
    },
    {
        id: 'scheduling',
        pattern: /agend|consulta|marcar|remarcar|desmarcar|agenda/,
        reply:
            'Posso orientar o agendamento. Nesta demonstração o fluxo é ilustrativo: eu confirmaria seu nome e um ' +
            'telefone para retorno, sua preferência de período (manhã ou tarde) e a disponibilidade da equipe. ' +
            'A secretaria da clínica validaria a data e enviaria a confirmação.\n\n' +
            'Não é necessário informar sintomas ou dados clínicos por este canal.\n\n' +
            'Na versão final, a solicitação será integrada diretamente à agenda da clínica.'
    },
    {
        id: 'doctors',
        pattern: /medic|equipe|neurocirurgi|especialista|doutor|profissionais/,
        reply:
            'A nossa equipe reúne neurocirurgiões com atuação em diferentes áreas.\n\n' +
            'Na versão final, posso apresentar o perfil de cada especialista — formação, áreas de atuação e agenda ' +
            'disponível — e direcionar o seu pedido ao profissional mais adequado.\n\n' +
            'Nesta demonstração os perfis ainda não estão cadastrados; a secretaria da clínica poderá fornecer as ' +
            'informações oficiais.'
    },
    {
        id: 'insurance',
        pattern: /convenio|plano de saude|particular|reembolso|cobertura|coparticipa|unimed|bradesco|sulamerica|amil/,
        reply:
            'Atendemos por convênios e também de forma particular. A lista oficial de convênios e as regras de ' +
            'cobertura serão configuradas nesta assistente antes da publicação.\n\n' +
            'A secretaria da clínica verifica a elegibilidade, a necessidade de autorização e as condições do seu ' +
            'plano. No caso de atendimento particular, também posso explicar como costuma funcionar o reembolso.'
    },
    {
        id: 'exams',
        pattern: /exame|ressonancia|tomografia|eletroneuromiografia|preparo|biopsia/,
        reply:
            'Posso ajudar com as informações administrativas dos exames: preparo indicado pela clínica, documentos ' +
            'necessários, prazos de laudo e autorização do convênio. Também registro solicitações de reagendamento.\n\n' +
            'Não realizo interpretação de resultados nem orientações clínicas — esses pontos são sempre conduzidos ' +
            'pelo médico responsável.'
    },
    {
        id: 'human',
        pattern: /atendente|humano|secretaria|falar com|telefone|whatsapp/,
        reply:
            'Posso encaminhar o seu atendimento à secretaria da clínica.\n\n' +
            'Nesta demonstração não há transferência real para uma pessoa. Na versão final, a conversa poderá ser ' +
            'direcionada à equipe responsável com o histórico do atendimento, preservando os dados do paciente.\n\n' +
            'Enquanto isso, posso ajudar com consultas, equipe médica, convênios, exames e localização.'
    },
    {
        id: 'greeting',
        pattern: /^(oi|ola|bom dia|boa tarde|boa noite|e ai)\b/,
        reply:
            'Olá! É um prazer atender você.\n\n' +
            'Posso ajudar com agendamentos, informações sobre a equipe médica, convênios, exames e localização. ' +
            'Sobre qual assunto você gostaria de falar?'
    },
    {
        id: 'thanks',
        pattern: /obrigad|valeu|agradec/,
        reply:
            'Por nada! Estou à disposição para ajudar com o que for necessário.\n\n' +
            'Se precisar, posso orientar sobre agendamento, equipe médica, convênios, exames ou localização.'
    }
];

const FALLBACK_REPLY =
    'Agradeço a sua mensagem. Nesta demonstração consigo simular apenas os assuntos administrativos principais: ' +
    'consultas, equipe médica, convênios, exames e localização.\n\n' +
    'Sobre "{trecho}": na versão final, essa solicitação será encaminhada ao assistente integrado à clínica, ' +
    'que responderá com as informações oficiais ou direcionará o atendimento à secretaria.';

const CONNECTION_ERROR_REPLY =
    'Não consegui concluir a conexão com o atendimento agora.\n\n' +
    'Verifique sua conexão e tente novamente. Se preferir, inicie uma nova conversa.';

/* --------------------------------------------------------------------------
   3. Referências do DOM e estado da aplicação
   -------------------------------------------------------------------------- */
const dom = {
    log: document.getElementById('chat-log'),
    typing: document.getElementById('typing-indicator'),
    typingStatus: document.getElementById('typing-status'),
    form: document.getElementById('chat-form'),
    input: document.getElementById('chat-input'),
    sendButton: document.getElementById('send-button'),
    newChatButton: document.getElementById('new-chat-button'),
    quickReplies: document.getElementById('quick-replies')
};

const chatState = {
    isSending: false,
    history: [],
    sessionId: 0,
    abortController: null
};

const timeFormatter = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
});
/* --------------------------------------------------------------------------
   4. Utilitários
   -------------------------------------------------------------------------- */

/** Mantém o texto do usuário íntegro para exibição (sem HTML). */
function normalizeInput(value) {
    return String(value == null ? '' : value)
        .replace(/\r\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
}

/** Remove acentos e caixa alta para facilitar a comparação por palavras-chave. */
function normalizeForMatching(text) {
    return text
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
}

function formatTime(date) {
    return timeFormatter.format(date);
}

function randomBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function wait(ms) {
    return new Promise(function (resolve) {
        window.setTimeout(resolve, ms);
    });
}

function scrollToLatest(behavior) {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const mode = behavior || (reduceMotion ? 'auto' : 'smooth');

    window.requestAnimationFrame(function () {
        dom.log.scrollTo({ top: dom.log.scrollHeight, behavior: mode });
    });
}

function autoResizeInput() {
    dom.input.style.height = 'auto';
    dom.input.style.height = Math.min(dom.input.scrollHeight, 132) + 'px';
}

/** Cria o avatar decorativo da assistente (SVG inline). */
function createAssistantAvatar(className) {
    const avatar = document.createElement('span');
    avatar.className = className;
    avatar.setAttribute('aria-hidden', 'true');
    avatar.innerHTML = '<svg viewBox="0 0 48 48" focusable="false"><use href="#icon-mark"></use></svg>';
    return avatar;
}

/**
 * Acrescenta uma mensagem ao histórico visual.
 * Todo o conteúdo é inserido com textContent (proteção contra HTML injetado).
 */
function appendMessage(role, text, options) {
    const settings = options || {};
    const isUser = role === 'user';

    const article = document.createElement('article');
    article.className = 'msg ' + (isUser ? 'msg--user' : 'msg--assistant');

    if (!isUser) {
        article.appendChild(createAssistantAvatar('msg__avatar'));
    }

    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble';

    if (settings.variant === 'error') {
        bubble.classList.add('msg__bubble--error');
    }

    if (settings.tag) {
        const tag = document.createElement('span');
        tag.className = 'msg__tag';
        tag.textContent = settings.tag;
        bubble.appendChild(tag);
    }

    const paragraph = document.createElement('p');
    paragraph.className = 'msg__text';

    const author = document.createElement('span');
    author.className = 'sr-only';
    author.textContent = isUser ? 'Você: ' : 'NeuroAssist: ';
    paragraph.appendChild(author);
    paragraph.appendChild(document.createTextNode(text));

    bubble.appendChild(paragraph);

    const meta = document.createElement('p');
    meta.className = 'msg__meta';

    const now = new Date();
    const time = document.createElement('time');
    time.dateTime = now.toISOString();
    time.textContent = formatTime(now);
    meta.appendChild(time);
    bubble.appendChild(meta);

    article.appendChild(bubble);

    // O indicador de digitação permanece sempre como último elemento
    dom.log.insertBefore(article, dom.typing);
    scrollToLatest();

    return article;
}

function showTyping() {
    dom.typing.hidden = false;
    dom.typingStatus.textContent = 'NeuroAssist está digitando…';
    scrollToLatest();
}

function hideTyping() {
    dom.typing.hidden = true;
    dom.typingStatus.textContent = '';
}

function updateSendButtonState() {
    const hasText = dom.input.value.trim().length > 0;
    dom.sendButton.disabled = chatState.isSending || !hasText;
}

function setSending(isSending) {
    chatState.isSending = isSending;
    dom.sendButton.classList.toggle('is-loading', isSending);
    dom.sendButton.setAttribute('aria-busy', String(isSending));
    dom.log.setAttribute('aria-busy', String(isSending));

    const chips = dom.quickReplies.querySelectorAll('.chip');
    chips.forEach(function (chip) {
        chip.setAttribute('aria-disabled', String(isSending));
        chip.tabIndex = isSending ? -1 : 0;
    });

    updateSendButtonState();
}

function resetComposer() {
    dom.input.value = '';
    autoResizeInput();
    updateSendButtonState();
}

function trimHistory() {
    const limit = NEURO_ASSIST_CONFIG.maxHistoryMessages;
    if (chatState.history.length > limit) {
        chatState.history = chatState.history.slice(-limit);
    }
}

/* --------------------------------------------------------------------------
   5. Respostas demonstrativas e integração HTTP
   -------------------------------------------------------------------------- */

/** Recorta um trecho da mensagem para citar na resposta padrão. */
function quoteSnippet(text) {
    const compact = text.replace(/\s+/g, ' ').trim();
    return compact.length > 70 ? compact.slice(0, 70) + '…' : compact;
}

/** Escolhe a resposta simulada conforme o assunto identificado. */
function buildDemoReply(message) {
    const normalized = normalizeForMatching(message);
    const rule = DEMO_RULES.find(function (item) {
        return item.pattern.test(normalized);
    });

    if (rule) {
        return rule.reply;
    }

    return FALLBACK_REPLY.replace('{trecho}', quoteSnippet(message));
}

/** Extrai o texto de resposta em diferentes formatos de JSON aceitos. */
function extractReplyText(payload) {
    if (typeof payload === 'string') {
        return payload.trim();
    }

    if (!payload || typeof payload !== 'object') {
        return '';
    }

    const candidates = [
        payload.reply,
        payload.message,
        payload.answer,
        payload.content,
        payload.output,
        payload.choices && payload.choices[0] && payload.choices[0].message
            ? payload.choices[0].message.content
            : ''
    ];

    for (const candidate of candidates) {
        if (typeof candidate === 'string' && candidate.trim()) {
            return candidate.trim();
        }
    }

    return '';
}

/**
 * Integração futura com o backend HTTP.
 * O backend é quem conversa com o Qwen no Strata — o navegador nunca recebe
 * credenciais, IPs internos ou portas.
 */
async function requestBackendReply(message) {
    const controller = new AbortController();
    chatState.abortController = controller;

    const timeoutId = window.setTimeout(function () {
        controller.abort();
    }, NEURO_ASSIST_CONFIG.requestTimeoutMs);

    try {
        const response = await fetch(NEURO_ASSIST_CONFIG.apiEndpoint, {
            method: 'POST',
            mode: 'cors',
            cache: 'no-store',
            credentials: 'omit',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: chatState.history
                    .slice(0, -1)
                    .slice(-NEURO_ASSIST_CONFIG.maxHistoryMessages),
                context: {
                    page: 'demo-clinica',
                    assistant: 'NeuroAssist',
                    channel: 'web'
                }
            }),
            signal: controller.signal
        });

        if (!response.ok) {
            throw new Error('Falha HTTP ' + response.status);
        }

        const contentType = response.headers.get('content-type') || '';
        let replyText = '';

        if (contentType.indexOf('application/json') !== -1) {
            replyText = extractReplyText(await response.json());
        } else {
            replyText = (await response.text()).trim();
        }

        if (!replyText) {
            throw new Error('Resposta vazia do backend');
        }

        return { text: replyText, simulated: false };
    } finally {
        window.clearTimeout(timeoutId);
        chatState.abortController = null;
    }
}

/**
 * Retorna a resposta da assistente.
 * Em modo de demonstração, aguarda o tempo do indicador de digitação e devolve
 * um conteúdo local identificado como simulação.
 */
async function getAssistantReply(message) {
    const useDemo =
        NEURO_ASSIST_CONFIG.demoMode ||
        !NEURO_ASSIST_CONFIG.apiEndpoint;

    if (useDemo) {
        const delay = NEURO_ASSIST_CONFIG.simulatedTypingDelay;
        await wait(randomBetween(delay.min, delay.max));
        return { text: buildDemoReply(message), simulated: true };
    }

    return requestBackendReply(message);
}

/* --------------------------------------------------------------------------
   6. Envio de mensagens (função pública para futura integração)
   -------------------------------------------------------------------------- */

/**
 * Envia uma mensagem do usuário e apresenta a resposta da assistente.
 * Função isolada e global — pode ser chamada pelo console ou por outro script:
 *   sendMessage('Olá');
 *
 * @param {string} message Texto digitado (ou acionado por um atalho).
 * @returns {Promise<boolean>} true quando a mensagem foi aceita.
 */
async function sendMessage(message) {
    const text = normalizeInput(message);

    if (!text || chatState.isSending) {
        return false;
    }

    const maxLength = NEURO_ASSIST_CONFIG.maxMessageLength;
    const safeText = text.length > maxLength ? text.slice(0, maxLength) : text;
    const session = chatState.sessionId;
    const shouldRestoreFocus = document.activeElement === dom.input;

    appendMessage('user', safeText);
    chatState.history.push({ role: 'user', content: safeText });
    trimHistory();
    resetComposer();

    setSending(true);
    showTyping();

    try {
        const reply = await getAssistantReply(safeText);

        // Uma nova conversa pode ter sido iniciada durante a espera
        if (session !== chatState.sessionId) {
            return true;
        }

        hideTyping();
        appendMessage('assistant', reply.text, {
            tag: reply.simulated ? 'Resposta simulada' : ''
        });
        chatState.history.push({ role: 'assistant', content: reply.text });
        trimHistory();
    } catch (error) {
        if (session !== chatState.sessionId) {
            return true;
        }

        hideTyping();
        appendMessage('assistant', CONNECTION_ERROR_REPLY, {
            tag: 'Falha na conexão',
            variant: 'error'
        });
    } finally {
        if (session === chatState.sessionId) {
            setSending(false);

            if (shouldRestoreFocus) {
                dom.input.focus();
            }
        }
    }

    return true;
}

/* --------------------------------------------------------------------------
   7. Controle da conversa
   -------------------------------------------------------------------------- */

/**
 * Reinicia a conversa, restaurando a mensagem inicial e limpando o histórico.
 * @param {{focus?: boolean}} [options]
 */
function startNewConversation(options) {
    const settings = options || {};

    chatState.sessionId += 1;

    if (chatState.abortController) {
        try {
            chatState.abortController.abort();
        } catch (error) {
            /* AbortController pode já estar finalizado — não há ação necessária */
        }
    }

    hideTyping();
    setSending(false);
    chatState.history = [];

    Array.from(dom.log.children).forEach(function (child) {
        if (child !== dom.typing) {
            child.remove();
        }
    });

    appendMessage('assistant', WELCOME_MESSAGE, {
        tag: 'Mensagem de demonstração'
    });

    resetComposer();

    if (settings.focus !== false) {
        dom.input.focus();
    }

    scrollToLatest('auto');
}

/* --------------------------------------------------------------------------
   8. Eventos
   -------------------------------------------------------------------------- */

dom.form.addEventListener('submit', function (event) {
    event.preventDefault();
    sendMessage(dom.input.value);
});

dom.input.addEventListener('keydown', function (event) {
    const isEnter = event.key === 'Enter' || event.keyCode === 13;

    if (isEnter && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        sendMessage(dom.input.value);
    }
});

dom.input.addEventListener('input', function () {
    autoResizeInput();
    updateSendButtonState();
});

dom.newChatButton.addEventListener('click', function () {
    startNewConversation();
});

dom.quickReplies.addEventListener('click', function (event) {
    const chip = event.target.closest('.chip');

    if (!chip) {
        return;
    }

    sendMessage(chip.dataset.question || chip.textContent);
});

/* --------------------------------------------------------------------------
   9. Inicialização e API pública
   -------------------------------------------------------------------------- */

/**
 * API exposta para a futura integração e para testes no console do navegador.
 * Exemplo: NeuroAssist.sendMessage('Quero agendar uma consulta')
 */
window.NeuroAssist = {
    sendMessage: sendMessage,
    startNewConversation: startNewConversation,
    getHistory: function () {
        return chatState.history.slice();
    },
    config: NEURO_ASSIST_CONFIG
};

startNewConversation({ focus: false });
autoResizeInput();
updateSendButtonState();

