import "@fontsource-variable/instrument-sans";
import "./app.css";
import "./lib/theme.svelte";   // el tema elegido, antes de dibujar nada
import { mount } from "svelte";
import App from "./App.svelte";

mount(App, { target: document.getElementById("app")! });
