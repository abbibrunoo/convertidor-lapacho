let productos = window.PRODUCTOS || [];

const productoBusqueda = document.getElementById("producto-busqueda");
const sugerencias = document.getElementById("producto-sugerencias");
const cantidadInput = document.getElementById("cantidad");
const precioInput = document.getElementById("precio-actualizado");
const totalResultado = document.getElementById("total-resultado");
const calcularBtn = document.getElementById("calcular-btn");
const listadoBtn = document.getElementById("listado-btn");
const listadoPanel = document.getElementById("listado-panel");
const listadoBusqueda = document.getElementById("listado-busqueda");
const listadoBuscarBtn = document.getElementById("listado-buscar-btn");
const listadoResultado = document.getElementById("listado-resultado");
const actualizarExcelBtn = document.getElementById("actualizar-excel-btn");
const totalProductos = document.getElementById("total-productos");
const excelActualizado = document.getElementById("excel-actualizado");
const productosTablaBody = document.getElementById("productos-tabla-body");
const productosMobileCards = document.getElementById("productos-mobile-cards");
let listadoFilas = Array.from(document.querySelectorAll(".table-wrap tbody tr"));
let listadoCards = Array.from(document.querySelectorAll(".mobile-cards .product-card"));

let productoSeleccionado = null;
let actualizandoProductos = false;

function normalizarTexto(texto) {
    return String(texto || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

function formatearMoneda(valor) {
    return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
    }).format(valor);
}

function escaparHtml(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function parsearCantidad(texto) {
    const limpio = String(texto || "").trim();
    if (!limpio) return NaN;
    return Number(limpio.replace(/\./g, "").replace(",", "."));
}

function buscarCoincidencias(termino) {
    const normalizado = normalizarTexto(termino);
    if (!normalizado) return [];
    return productos.filter((item) => normalizarTexto(item.etiqueta).includes(normalizado));
}

function intentarSeleccionAutomatica() {
    const termino = productoBusqueda.value;
    const coincidencias = buscarCoincidencias(termino);
    const terminoNormalizado = normalizarTexto(termino);

    if (!terminoNormalizado) {
        productoSeleccionado = null;
        precioInput.value = "$ 0,00";
        return false;
    }

    const exacta = coincidencias.find((item) => normalizarTexto(item.etiqueta) === terminoNormalizado);
    const candidata = exacta || (coincidencias.length === 1 ? coincidencias[0] : null);

    if (candidata) {
        seleccionarProducto(candidata);
        return true;
    }

    productoSeleccionado = null;
    precioInput.value = "$ 0,00";
    return false;
}

function renderSugerencias(items) {
    sugerencias.innerHTML = "";

    if (!items.length) {
        sugerencias.hidden = true;
        return;
    }

    items.forEach((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "suggestion-item";
        button.innerHTML = `
            <span class="suggestion-main">${item.producto}</span>
            <span class="suggestion-meta">${item.categoria} ${item.unidad ? `| ${item.unidad}` : ""} | ${item.precio_formateado}</span>
        `;
        button.addEventListener("click", () => seleccionarProducto(item));
        sugerencias.appendChild(button);
    });

    sugerencias.hidden = false;
}

function seleccionarProducto(item) {
    productoSeleccionado = item;
    productoBusqueda.value = item.etiqueta;
    precioInput.value = item.precio_formateado;
    sugerencias.hidden = true;
}

function textoBusquedaProducto(item) {
    return `${item.categoria || ""} ${item.producto || ""} ${item.unidad || ""} ${item.fuente || ""}`.toLowerCase();
}

function renderListadoCompleto() {
    productosTablaBody.innerHTML = productos.map((item) => `
        <tr data-search="${escaparHtml(textoBusquedaProducto(item))}">
            <td>${escaparHtml(item.categoria)}</td>
            <td>${escaparHtml(item.producto)}</td>
            <td>${escaparHtml(item.unidad)}</td>
            <td>${escaparHtml(item.precio_formateado)}</td>
            <td>${escaparHtml(item.fuente)}</td>
        </tr>
    `).join("");

    productosMobileCards.innerHTML = productos.map((item) => `
        <article class="product-card" data-search="${escaparHtml(textoBusquedaProducto(item))}">
            <div class="product-card__top">
                <span class="product-card__category">${escaparHtml(item.categoria)}</span>
                <strong class="product-card__price">${escaparHtml(item.precio_formateado)}</strong>
            </div>
            <h3>${escaparHtml(item.producto)}</h3>
            <div class="product-card__meta">
                <span>Unidad: ${escaparHtml(item.unidad || "-")}</span>
                <span>Fuente: ${escaparHtml(item.fuente)}</span>
            </div>
        </article>
    `).join("");

    listadoFilas = Array.from(document.querySelectorAll(".table-wrap tbody tr"));
    listadoCards = Array.from(document.querySelectorAll(".mobile-cards .product-card"));
    filtrarListado();
}

async function actualizarProductosDesdeExcel() {
    if (actualizandoProductos) return;

    actualizandoProductos = true;
    const textoOriginal = actualizarExcelBtn ? actualizarExcelBtn.textContent : "";
    if (actualizarExcelBtn) {
        actualizarExcelBtn.disabled = true;
        actualizarExcelBtn.textContent = "Actualizando...";
    }

    try {
        const respuesta = await fetch(`/api/productos?t=${Date.now()}`, { cache: "no-store" });
        if (!respuesta.ok) throw new Error("No se pudo actualizar");

        const data = await respuesta.json();
        productos = data.productos || [];
        totalProductos.textContent = data.total_productos;
        excelActualizado.textContent = data.excel_actualizado ? ` | Actualizado ${data.excel_actualizado}` : "";

        if (productoSeleccionado) {
            productoSeleccionado = productos.find((item) => item.etiqueta === productoSeleccionado.etiqueta) || null;
            precioInput.value = productoSeleccionado ? productoSeleccionado.precio_formateado : "$ 0,00";
        }

        renderListadoCompleto();
    } catch (error) {
        listadoResultado.textContent = "No se pudo actualizar el Excel. Guardalo y volve a intentar.";
    } finally {
        actualizandoProductos = false;
        if (actualizarExcelBtn) {
            actualizarExcelBtn.disabled = false;
            actualizarExcelBtn.textContent = textoOriginal || "Actualizar Excel";
        }
    }
}

function buscarProductos() {
    const termino = normalizarTexto(productoBusqueda.value);
    if (!termino) {
        renderSugerencias(productos.slice(0, 8));
        return;
    }

    const coincidencias = productos
        .filter((item) => normalizarTexto(item.etiqueta).includes(termino))
        .slice(0, 12);

    renderSugerencias(coincidencias);
}

function calcularTotal() {
    if (!productoSeleccionado) {
        intentarSeleccionAutomatica();
    }

    if (!productoSeleccionado) {
        totalResultado.textContent = "Seleccioná un producto";
        return;
    }

    const cantidad = parsearCantidad(cantidadInput.value);
    if (Number.isNaN(cantidad)) {
        totalResultado.textContent = "Cantidad inválida";
        return;
    }

    const total = cantidad * productoSeleccionado.precio;
    totalResultado.textContent = formatearMoneda(total);
}

function filtrarListado() {
    const termino = normalizarTexto(listadoBusqueda.value);
    let visibles = 0;

    listadoFilas.forEach((fila) => {
        const texto = normalizarTexto(fila.dataset.search || "");
        const mostrar = !termino || texto.includes(termino);
        fila.hidden = !mostrar;
        if (mostrar) visibles += 1;
    });

    listadoCards.forEach((card) => {
        const texto = normalizarTexto(card.dataset.search || "");
        const mostrar = !termino || texto.includes(termino);
        card.hidden = !mostrar;
    });

    if (!termino) {
        listadoResultado.textContent = "Mostrando todos los productos.";
    } else if (visibles === 0) {
        listadoResultado.textContent = "No se encontraron productos con esa búsqueda.";
    } else {
        listadoResultado.textContent = `Se encontraron ${visibles} producto(s).`;
    }
}

productoBusqueda.addEventListener("focus", buscarProductos);
productoBusqueda.addEventListener("input", () => {
    intentarSeleccionAutomatica();
    buscarProductos();
});

cantidadInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        calcularTotal();
    }
});

calcularBtn.addEventListener("click", calcularTotal);

listadoBuscarBtn.addEventListener("click", filtrarListado);
actualizarExcelBtn.addEventListener("click", actualizarProductosDesdeExcel);

listadoBusqueda.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        filtrarListado();
    }
});

listadoBtn.addEventListener("click", () => {
    const estabaOculto = listadoPanel.hidden;
    listadoPanel.hidden = !estabaOculto;
    listadoBtn.textContent = estabaOculto ? "Ocultar listado" : "Listado";

    if (estabaOculto) {
        actualizarProductosDesdeExcel();
        listadoPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
});

document.addEventListener("click", (event) => {
    if (!sugerencias.contains(event.target) && event.target !== productoBusqueda) {
        sugerencias.hidden = true;
    }
});
