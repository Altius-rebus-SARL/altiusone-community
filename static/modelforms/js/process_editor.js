/**
 * Process Editor — Force-directed graph workflow builder
 *
 * Usage:  ProcessEditor.init({ containerId, stepsInputId, transitionsInputId, graphUrl, readOnly, pollUrl, pollInterval })
 *
 * Depends on D3 v7 (loaded by {% d3_scripts %}).
 */
(function () {
    "use strict";

    /* ===================== colour map ===================== */
    const STEP_COLORS = {
        START: "#28a745", END: "#dc3545",
        FORM_FILL: "#0d6efd", DOCUMENT_UPLOAD: "#6610f2",
        HUMAN_APPROVAL: "#fd7e14", CALCULATION: "#20c997",
        CREATE_OBJECT: "#0dcaf0", SEND_EMAIL: "#6f42c1",
        SEND_NOTIFICATION: "#d63384", CREATE_TASK: "#ffc107",
        WEBHOOK: "#198754", CONDITIONAL: "#adb5bd",
        LOOP: "#6c757d", WAIT: "#495057",
    };

    const STEP_ICONS = {
        START: "▶", END: "■",
        FORM_FILL: "📝", DOCUMENT_UPLOAD: "📄",
        HUMAN_APPROVAL: "👤", CALCULATION: "🔢",
        CREATE_OBJECT: "➕", SEND_EMAIL: "✉",
        SEND_NOTIFICATION: "🔔", CREATE_TASK: "☑",
        WEBHOOK: "🌐", CONDITIONAL: "◆",
        LOOP: "🔁", WAIT: "⏳",
    };

    /* ===================== state ===================== */
    let nodes = [];      // {id, name, step_type, configuration, conditions, order, x, y, ...}
    let links = [];      // {source, target, label, condition, ...}
    let selected = null; // {type: 'node'|'link', data}
    let simulation, svg, g, linkG, nodeG, tempLine;
    let width, height;
    let opts = {};
    let linking = null;  // when creating an edge: {sourceNode}
    let nextOrder = 1;

    /* ===================== init ===================== */
    function init(options) {
        opts = Object.assign({
            containerId: "process-canvas",
            stepsInputId: "id_steps_json",
            transitionsInputId: "id_transitions_json",
            graphUrl: null,
            readOnly: false,
            pollUrl: null,
            pollInterval: 3,
        }, options);

        const container = document.getElementById(opts.containerId);
        if (!container) return;

        const rect = container.getBoundingClientRect();
        width = rect.width || 800;
        height = Math.max(rect.height, 520);

        /* Load initial data from hidden inputs or API */
        if (opts.graphUrl) {
            fetch(opts.graphUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(r => r.json())
                .then(data => {
                    nodes = data.nodes || [];
                    links = (data.links || []).map(normalizeLink);
                    nextOrder = nodes.reduce((m, n) => Math.max(m, (n.order || 0) + 1), 1);
                    buildSVG(container);
                    render();
                    if (opts.pollUrl) startPolling();
                });
        } else {
            loadFromInputs();
            buildSVG(container);
            render();
        }

        /* Palette drag & drop */
        if (!opts.readOnly) setupPaletteDrag(container);
    }

    function normalizeLink(l) {
        return {
            source: typeof l.source === "object" ? l.source.id : l.source,
            target: typeof l.target === "object" ? l.target.id : l.target,
            label: l.label || "",
            condition: l.condition || {},
        };
    }

    function loadFromInputs() {
        try {
            const stepsEl = document.getElementById(opts.stepsInputId);
            const transEl = document.getElementById(opts.transitionsInputId);
            if (stepsEl && stepsEl.value) nodes = JSON.parse(stepsEl.value);
            if (transEl && transEl.value) {
                links = JSON.parse(transEl.value).map(t => ({
                    source: t.from || t.source,
                    target: t.to || t.target,
                    label: t.label || "",
                    condition: t.condition || {},
                }));
            }
        } catch (e) { console.warn("ProcessEditor: parse error", e); }
        /* Assign default positions if missing */
        nodes.forEach((n, i) => {
            if (!n.x && !n.position_x) { n.x = 120 + (i % 5) * 160; }
            else if (n.position_x) { n.x = n.position_x; }
            if (!n.y && !n.position_y) { n.y = 80 + Math.floor(i / 5) * 120; }
            else if (n.position_y) { n.y = n.position_y; }
            n.id = n.id || n.code;
            n.color = STEP_COLORS[n.step_type] || "#6c757d";
        });
        nextOrder = nodes.reduce((m, n) => Math.max(m, (n.order || 0) + 1), 1);
    }

    /* ===================== SVG setup ===================== */
    function buildSVG(container) {
        d3.select(container).select("svg").remove();

        svg = d3.select(container)
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        /* Arrow marker */
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 28).attr("refY", 0)
            .attr("markerWidth", 8).attr("markerHeight", 8)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#999");

        /* Zoom layer */
        g = svg.append("g");
        const zoom = d3.zoom()
            .scaleExtent([0.3, 3])
            .on("zoom", e => g.attr("transform", e.transform));
        svg.call(zoom);

        /* Click on background to deselect */
        svg.on("click", function (e) {
            if (e.target === svg.node() || e.target === g.node()) {
                deselect();
                cancelLinking();
            }
        });

        /* Double-click on background to add node */
        if (!opts.readOnly) {
            svg.on("dblclick", function (e) {
                if (e.target !== svg.node() && !e.target.closest?.("g.pe-link")) return;
                const [mx, my] = d3.pointer(e, g.node());
                addNode("FORM_FILL", mx, my);
            });
        }

        /* Keyboard */
        d3.select("body").on("keydown.pe", function (e) {
            if (opts.readOnly) return;
            if (e.key === "Delete" || e.key === "Backspace") {
                if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") return;
                if (selected) { deleteSelected(); e.preventDefault(); }
            }
            if (e.key === "Escape") {
                cancelLinking();
                deselect();
            }
        });

        linkG = g.append("g").attr("class", "pe-links");
        nodeG = g.append("g").attr("class", "pe-nodes");
        tempLine = g.append("line").attr("class", "pe-temp-link").style("display", "none");

        /* Simulation */
        simulation = d3.forceSimulation()
            .force("charge", d3.forceManyBody().strength(-300))
            .force("link", d3.forceLink().id(d => d.id).distance(140))
            .force("x", d3.forceX(width / 2).strength(0.02))
            .force("y", d3.forceY(height / 2).strength(0.02))
            .force("collision", d3.forceCollide(40))
            .alphaDecay(0.05)
            .on("tick", ticked);

        /* If nodes have positions, use them as fixed */
        nodes.forEach(n => {
            if (n.x && n.y) { n.fx = n.x; n.fy = n.y; }
        });
    }

    /* ===================== render ===================== */
    function render() {
        /* --- LINKS --- */
        const linkSel = linkG.selectAll("g.pe-link")
            .data(links, d => d.source + "->" + d.target);

        linkSel.exit().remove();

        const linkEnter = linkSel.enter().append("g").attr("class", "pe-link");
        linkEnter.append("line");
        linkEnter.append("text").attr("dy", -6);

        if (!opts.readOnly) {
            linkEnter.on("click", function (e, d) {
                e.stopPropagation();
                selectLink(d);
            });
        }

        const linkAll = linkEnter.merge(linkSel);
        linkAll.select("text").text(d => d.label || "");
        linkAll.classed("selected", d => selected && selected.type === "link" && selected.data === d);

        /* --- NODES --- */
        const nodeSel = nodeG.selectAll("g.pe-node")
            .data(nodes, d => d.id);

        nodeSel.exit().remove();

        const nodeEnter = nodeSel.enter().append("g").attr("class", "pe-node");
        nodeEnter.append("circle").attr("r", 18);
        nodeEnter.append("text").attr("class", "pe-node-icon").attr("dy", 1);
        nodeEnter.append("text").attr("class", "pe-node-label").attr("dy", 32);
        nodeEnter.append("text").attr("class", "pe-node-type").attr("dy", 44);

        if (!opts.readOnly) {
            nodeEnter.call(d3.drag()
                .on("start", dragStart)
                .on("drag", dragged)
                .on("end", dragEnd));

            nodeEnter.on("click", function (e, d) {
                e.stopPropagation();
                if (linking) {
                    finishLinking(d);
                } else {
                    selectNode(d);
                }
            });

            /* Right-click on node: start creating edge */
            nodeEnter.on("contextmenu", function (e, d) {
                e.preventDefault();
                e.stopPropagation();
                startLinking(d);
            });
        }

        const nodeAll = nodeEnter.merge(nodeSel);
        nodeAll.select("circle")
            .attr("fill", d => d.color || STEP_COLORS[d.step_type] || "#6c757d")
            .attr("r", d => (d.step_type === "START" || d.step_type === "END") ? 16 : 18);
        nodeAll.select(".pe-node-icon")
            .text(d => STEP_ICONS[d.step_type] || "●");
        nodeAll.select(".pe-node-label")
            .text(d => d.name || d.id);
        nodeAll.select(".pe-node-type")
            .text(d => d.step_type);
        nodeAll.classed("selected", d => selected && selected.type === "node" && selected.data === d);

        /* Status classes for live view */
        nodeAll.each(function (d) {
            const el = d3.select(this).select("circle");
            el.classed("pe-status-COMPLETED", d.status === "COMPLETED");
            el.classed("pe-status-RUNNING", d.status === "RUNNING");
            el.classed("pe-status-WAITING", d.status === "WAITING");
            el.classed("pe-status-FAILED", d.status === "FAILED");
            el.classed("pe-status-PENDING", d.status === "PENDING");
        });

        /* Update simulation */
        simulation.nodes(nodes);
        simulation.force("link").links(
            links.map(l => ({
                source: typeof l.source === "string" ? l.source : l.source.id,
                target: typeof l.target === "string" ? l.target : l.target.id,
            }))
        );
        simulation.alpha(0.3).restart();
    }

    function ticked() {
        linkG.selectAll("g.pe-link").each(function (d) {
            const src = findNode(typeof d.source === "string" ? d.source : d.source.id);
            const tgt = findNode(typeof d.target === "string" ? d.target : d.target.id);
            if (!src || !tgt) return;
            d3.select(this).select("line")
                .attr("x1", src.x).attr("y1", src.y)
                .attr("x2", tgt.x).attr("y2", tgt.y);
            d3.select(this).select("text")
                .attr("x", (src.x + tgt.x) / 2)
                .attr("y", (src.y + tgt.y) / 2);
        });
        nodeG.selectAll("g.pe-node")
            .attr("transform", d => `translate(${d.x},${d.y})`);
    }

    function findNode(id) { return nodes.find(n => n.id === id); }

    /* ===================== drag nodes ===================== */
    function dragStart(e, d) {
        if (!e.active) simulation.alphaTarget(0.1).restart();
        d.fx = d.x; d.fy = d.y;
    }
    function dragged(e, d) {
        d.fx = e.x; d.fy = e.y;
    }
    function dragEnd(e, d) {
        if (!e.active) simulation.alphaTarget(0);
        /* Keep position fixed after drag */
        d.fx = d.x; d.fy = d.y;
        syncToInputs();
    }

    /* ===================== selection ===================== */
    function selectNode(d) {
        selected = { type: "node", data: d };
        render();
        showNodeConfig(d);
    }
    function selectLink(d) {
        selected = { type: "link", data: d };
        render();
        showLinkConfig(d);
    }
    function deselect() {
        selected = null;
        render();
        hideConfig();
    }

    /* ===================== linking (create edge) ===================== */
    function startLinking(sourceNode) {
        linking = { sourceNode };
        svg.on("mousemove.linking", function (e) {
            const [mx, my] = d3.pointer(e, g.node());
            tempLine
                .style("display", null)
                .attr("x1", sourceNode.x)
                .attr("y1", sourceNode.y)
                .attr("x2", mx)
                .attr("y2", my);
        });
        document.getElementById(opts.containerId).style.cursor = "crosshair";
    }

    function finishLinking(targetNode) {
        if (!linking) return;
        const src = linking.sourceNode;
        if (src.id === targetNode.id) { cancelLinking(); return; }
        /* Check no duplicate */
        const exists = links.some(l =>
            (getNodeId(l.source) === src.id && getNodeId(l.target) === targetNode.id)
        );
        if (!exists) {
            links.push({ source: src.id, target: targetNode.id, label: "", condition: {} });
            syncToInputs();
        }
        cancelLinking();
        render();
    }

    function cancelLinking() {
        linking = null;
        tempLine.style("display", "none");
        svg.on("mousemove.linking", null);
        const el = document.getElementById(opts.containerId);
        if (el) el.style.cursor = "";
    }

    function getNodeId(n) { return typeof n === "string" ? n : n.id; }

    /* ===================== add / delete ===================== */
    function addNode(stepType, x, y, name) {
        const code = stepType + "_" + String(nextOrder).padStart(2, "0");
        const node = {
            id: code,
            code: code,
            name: name || code.replace(/_/g, " "),
            step_type: stepType,
            configuration: {},
            conditions: {},
            order: nextOrder++,
            x: x || width / 2,
            y: y || height / 2,
            fx: x || width / 2,
            fy: y || height / 2,
            color: STEP_COLORS[stepType] || "#6c757d",
        };
        nodes.push(node);
        render();
        syncToInputs();
        selectNode(node);
        return node;
    }

    function deleteSelected() {
        if (!selected) return;
        if (selected.type === "node") {
            const id = selected.data.id;
            nodes = nodes.filter(n => n.id !== id);
            links = links.filter(l => getNodeId(l.source) !== id && getNodeId(l.target) !== id);
        } else if (selected.type === "link") {
            const d = selected.data;
            links = links.filter(l => l !== d);
        }
        selected = null;
        render();
        syncToInputs();
        hideConfig();
    }

    /* ===================== config panel ===================== */
    function showNodeConfig(d) {
        const panel = document.getElementById("pe-config-content");
        if (!panel) return;

        panel.innerHTML = `
            <h6 class="mb-3"><span class="pe-palette-dot d-inline-block" style="background:${d.color};width:10px;height:10px;border-radius:50%"></span> ${d.step_type}</h6>
            <div class="mb-2">
                <label class="form-label">Code</label>
                <input type="text" class="form-control form-control-sm" id="pe-cfg-code" value="${escHtml(d.id)}">
            </div>
            <div class="mb-2">
                <label class="form-label">Nom</label>
                <input type="text" class="form-control form-control-sm" id="pe-cfg-name" value="${escHtml(d.name)}">
            </div>
            <div class="mb-2">
                <label class="form-label">Type</label>
                <select class="form-select form-select-sm" id="pe-cfg-type">
                    ${Object.keys(STEP_COLORS).map(t =>
                        `<option value="${t}" ${t === d.step_type ? "selected" : ""}>${t}</option>`
                    ).join("")}
                </select>
            </div>
            <div class="mb-2">
                <label class="form-label">Configuration (JSON)</label>
                <textarea class="form-control form-control-sm json-edit" id="pe-cfg-config" rows="5">${escHtml(JSON.stringify(d.configuration || {}, null, 2))}</textarea>
            </div>
            <div class="mb-2">
                <label class="form-label">Conditions (JSON)</label>
                <textarea class="form-control form-control-sm json-edit" id="pe-cfg-conditions" rows="3">${escHtml(JSON.stringify(d.conditions || {}, null, 2))}</textarea>
            </div>
            <div class="d-flex gap-2 mt-3">
                <button type="button" class="btn btn-sm btn-primary flex-fill" id="pe-cfg-save">Appliquer</button>
                <button type="button" class="btn btn-sm btn-outline-danger" id="pe-cfg-delete">
                    <i class="ti ti-trash"></i>
                </button>
            </div>
        `;

        document.getElementById("pe-cfg-save").onclick = function () {
            const oldId = d.id;
            const newCode = document.getElementById("pe-cfg-code").value.trim();
            d.name = document.getElementById("pe-cfg-name").value.trim();
            d.step_type = document.getElementById("pe-cfg-type").value;
            d.color = STEP_COLORS[d.step_type] || "#6c757d";
            try { d.configuration = JSON.parse(document.getElementById("pe-cfg-config").value); } catch (_) {}
            try { d.conditions = JSON.parse(document.getElementById("pe-cfg-conditions").value); } catch (_) {}

            /* Rename id if changed */
            if (newCode && newCode !== oldId) {
                d.id = newCode;
                d.code = newCode;
                links.forEach(l => {
                    if (getNodeId(l.source) === oldId) l.source = newCode;
                    if (getNodeId(l.target) === oldId) l.target = newCode;
                });
            }
            render();
            syncToInputs();
        };

        document.getElementById("pe-cfg-delete").onclick = function () {
            deleteSelected();
        };
    }

    function showLinkConfig(d) {
        const panel = document.getElementById("pe-config-content");
        if (!panel) return;

        panel.innerHTML = `
            <h6 class="mb-3">Transition</h6>
            <div class="mb-2">
                <label class="form-label">De</label>
                <input type="text" class="form-control form-control-sm" value="${escHtml(getNodeId(d.source))}" readonly>
            </div>
            <div class="mb-2">
                <label class="form-label">Vers</label>
                <input type="text" class="form-control form-control-sm" value="${escHtml(getNodeId(d.target))}" readonly>
            </div>
            <div class="mb-2">
                <label class="form-label">Libellé</label>
                <input type="text" class="form-control form-control-sm" id="pe-link-label" value="${escHtml(d.label)}">
            </div>
            <div class="mb-2">
                <label class="form-label">Condition (JSON)</label>
                <textarea class="form-control form-control-sm json-edit" id="pe-link-condition" rows="4">${escHtml(JSON.stringify(d.condition || {}, null, 2))}</textarea>
            </div>
            <div class="d-flex gap-2 mt-3">
                <button type="button" class="btn btn-sm btn-primary flex-fill" id="pe-link-save">Appliquer</button>
                <button type="button" class="btn btn-sm btn-outline-danger" id="pe-link-delete">
                    <i class="ti ti-trash"></i>
                </button>
            </div>
        `;

        document.getElementById("pe-link-save").onclick = function () {
            d.label = document.getElementById("pe-link-label").value.trim();
            try { d.condition = JSON.parse(document.getElementById("pe-link-condition").value); } catch (_) {}
            render();
            syncToInputs();
        };

        document.getElementById("pe-link-delete").onclick = function () {
            deleteSelected();
        };
    }

    function hideConfig() {
        const panel = document.getElementById("pe-config-content");
        if (panel) {
            panel.innerHTML = `
                <p class="text-muted f-s-12 text-center mt-4">
                    Cliquez sur un nœud ou une transition pour modifier ses propriétés.<br><br>
                    <strong>Raccourcis :</strong><br>
                    <kbd>Clic droit</kbd> sur nœud → créer transition<br>
                    <kbd>Double clic</kbd> sur fond → nouveau nœud<br>
                    <kbd>Suppr</kbd> → supprimer sélection<br>
                    <kbd>Esc</kbd> → annuler
                </p>
            `;
        }
    }

    /* ===================== palette drag & drop ===================== */
    function setupPaletteDrag(container) {
        document.querySelectorAll(".pe-palette-item").forEach(item => {
            item.setAttribute("draggable", "true");
            item.addEventListener("dragstart", function (e) {
                e.dataTransfer.setData("text/plain", this.dataset.stepType);
                e.dataTransfer.effectAllowed = "copy";
            });
        });

        container.addEventListener("dragover", function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            container.classList.add("drag-over");
        });
        container.addEventListener("dragleave", function () {
            container.classList.remove("drag-over");
        });
        container.addEventListener("drop", function (e) {
            e.preventDefault();
            container.classList.remove("drag-over");
            const stepType = e.dataTransfer.getData("text/plain");
            if (!stepType || !STEP_COLORS[stepType]) return;
            /* Compute position relative to the SVG transform */
            const svgRect = svg.node().getBoundingClientRect();
            const transform = d3.zoomTransform(svg.node());
            const x = (e.clientX - svgRect.left - transform.x) / transform.k;
            const y = (e.clientY - svgRect.top - transform.y) / transform.k;
            addNode(stepType, x, y);
        });
    }

    /* ===================== sync state → hidden inputs ===================== */
    function syncToInputs() {
        const stepsEl = document.getElementById(opts.stepsInputId);
        const transEl = document.getElementById(opts.transitionsInputId);

        if (stepsEl) {
            stepsEl.value = JSON.stringify(nodes.map((n, i) => ({
                code: n.id,
                name: n.name,
                description: n.description || "",
                step_type: n.step_type,
                configuration: n.configuration || {},
                conditions: n.conditions || {},
                order: n.order || i,
                max_retries: n.max_retries || 0,
                retry_delay_seconds: n.retry_delay_seconds || 60,
                timeout_seconds: n.timeout_seconds || null,
                position_x: Math.round(n.x || 0),
                position_y: Math.round(n.y || 0),
            })), null, 2);
        }
        if (transEl) {
            transEl.value = JSON.stringify(links.map((l, i) => ({
                from: getNodeId(l.source),
                to: getNodeId(l.target),
                label: l.label || "",
                condition: l.condition || {},
                order: i,
            })), null, 2);
        }
    }

    /* ===================== polling (live execution view) ===================== */
    function startPolling() {
        if (!opts.pollUrl) return;
        setInterval(function () {
            fetch(opts.pollUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(r => r.json())
                .then(data => {
                    /* Update node statuses */
                    (data.nodes || []).forEach(sn => {
                        const node = findNode(sn.id);
                        if (node) {
                            node.status = sn.status;
                            node.is_current = sn.is_current;
                        }
                    });
                    /* Update instance status banner */
                    const banner = document.getElementById("pe-instance-status");
                    if (banner) {
                        banner.textContent = data.status;
                        banner.className = "badge " + statusBadgeClass(data.status);
                    }
                    render();
                })
                .catch(() => {});
        }, opts.pollInterval * 1000);
    }

    function statusBadgeClass(s) {
        return {
            COMPLETED: "bg-success", FAILED: "bg-danger",
            RUNNING: "bg-info", WAITING: "bg-warning",
            PENDING: "bg-secondary", CANCELLED: "bg-dark",
        }[s] || "bg-secondary";
    }

    /* ===================== utils ===================== */
    function escHtml(s) {
        if (s == null) return "";
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    /* ===================== public API ===================== */
    window.ProcessEditor = {
        init: init,
        addNode: addNode,
        getNodes: function () { return nodes; },
        getLinks: function () { return links; },
        syncToInputs: syncToInputs,
    };
})();
