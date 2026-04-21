const productos = window.PRODUCTOS || [];

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
const listadoFilas = Array.from(document.querySelectorAll(".table-wrap tbody tr"));
const listadoCards = Array.from(document.querySelectorAll(".mobile-cards .product-card"));
const menuToggle = document.getElementById("menu-toggle");
const menuDropdown = document.getElementById("menu-dropdown");

let productoSeleccionado = null;

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

function parsearCantidad(texto) {
    const limpio = String(texto || "").trim();
    if (!limpio) return NaN;
    return Number(limpio.replace(/\./g, "").replace(",", "."));
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

function toggleMenu(forceState) {
    if (!menuToggle || !menuDropdown) return;

    const shouldOpen = typeof forceState === "boolean" ? forceState : menuDropdown.hidden;
    menuDropdown.hidden = !shouldOpen;
    menuToggle.setAttribute("aria-expanded", String(shouldOpen));
}

productoBusqueda.addEventListener("focus", buscarProductos);
productoBusqueda.addEventListener("input", () => {
    productoSeleccionado = null;
    precioInput.value = "$ 0,00";
    buscarProductos();
});

cantidadInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        calcularTotal();
    }
});

calcularBtn.addEventListener("click", calcularTotal);

listadoBuscarBtn.addEventListener("click", filtrarListado);

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
        listadoPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
});

if (menuToggle) {
    menuToggle.addEventListener("click", () => toggleMenu());
}

document.addEventListener("click", (event) => {
    if (!sugerencias.contains(event.target) && event.target !== productoBusqueda) {
        sugerencias.hidden = true;
    }

    if (menuDropdown && menuToggle) {
        const clickDentroMenu = menuDropdown.contains(event.target) || menuToggle.contains(event.target);
        if (!clickDentroMenu) {
            toggleMenu(false);
        }
    }
});
