// andamio de escritorio: una ventana que arranca el panel de andamio (`andamio ui`) y lo muestra.
//
// El panel es el mismo de siempre: corre en tu máquina (en Windows, dentro de WSL), solo en
// 127.0.0.1, con su clave en el link. La app:
//  1. lo arranca con --desktop (se apaga solo cuando su entrada se cierra) y lee su dirección;
//  2. muestra una página de arranque mientras tanto, o el error si no pudo (con "Reintentar");
//  3. abre los links de afuera (GitHub, tu dominio) en tu navegador, no dentro de la ventana;
//  4. al cerrarse, cierra la entrada del panel: el panel termina limpio;
//  5. busca una versión nueva firmada con tu llave y, si la hay, pregunta antes de instalarla; mientras
//     se descarga e instala, la ventana lo muestra (y si falla, dice por qué y vuelve al panel).
// Lo que pasa con las actualizaciones queda en un registro (andamio.log): en Windows
// %LOCALAPPDATA%\me.andamio.desktop\logs, en Linux ~/.local/share/me.andamio.desktop/logs y en
// macOS ~/Library/Logs/me.andamio.desktop.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::net::{SocketAddr, TcpStream};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::io::Write as _;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent, Url, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_updater::UpdaterExt;

/// El panel que corre por detrás, el error de arranque (si lo hubo) para la página de inicio, y una
/// actualización en curso (fase, bytes bajados, error) para mostrarla en la ventana.
#[derive(Default)]
struct Panel {
    child: Mutex<Option<Child>>,
    stdin: Mutex<Option<ChildStdin>>,
    error: Mutex<Option<String>>,
    url: Mutex<Option<String>>,
    update_phase: Mutex<Option<String>>,
    update_done: AtomicU64,
    update_total: AtomicU64,
    update_error: Mutex<Option<String>>,
}

/// Una línea en el registro de la app (con fecha), para saber qué pasó si algo falla en silencio.
fn log(app: &AppHandle, msg: &str) {
    let Ok(dir) = app.path().app_log_dir() else { return };
    let _ = std::fs::create_dir_all(&dir);
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(dir.join("andamio.log")) {
        let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
        let _ = writeln!(f, "{secs} {msg}");
    }
}

/// La página de la app (arranque, actualización), en Windows y en los demás.
fn local_page(fragment: &str) -> Option<Url> {
    let base = if cfg!(windows) { "http://tauri.localhost/index.html" } else { "tauri://localhost/index.html" };
    Url::parse(&format!("{base}{fragment}")).ok()
}

/// Mensajes en el idioma del sistema (español o inglés).
fn l(es: &str, en: &str) -> String {
    let lang = sys_locale::get_locale().unwrap_or_default().to_lowercase();
    if lang.starts_with("es") { es.to_string() } else { en.to_string() }
}

/// `andamio ui` desde la carpeta de inicio: el comando global usa la copia elegida (andamio use).
fn panel_command() -> Command {
    let script = "cd ~ && exec andamio ui --no-browser --desktop";
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let mut c = Command::new("wsl.exe");
        c.args(["-e", "bash", "-lc", script]);
        c.creation_flags(0x0800_0000); // CREATE_NO_WINDOW: sin consola negra
        c
    }
    // Linux y macOS: con tu shell de login (lee tu .profile / .zprofile). Una app abierta desde el
    // escritorio no hereda el PATH de tu terminal: se suman donde lo dejan andamio setup y Homebrew.
    #[cfg(not(windows))]
    {
        let shell = std::env::var("SHELL").ok().filter(|s| !s.is_empty()).unwrap_or_else(|| "/bin/bash".into());
        let home = std::env::var("HOME").unwrap_or_default();
        let path = std::env::var("PATH").unwrap_or_default();
        let mut c = Command::new(shell);
        c.args(["-lc", script]);
        c.env("PATH", format!("{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:{path}"));
        c
    }
}

/// Dónde corre andamio: dentro de WSL en Windows, en la misma máquina en los demás.
fn where_andamio() -> (&'static str, &'static str) {
    if cfg!(windows) { (" dentro de WSL", " inside WSL") } else { ("", "") }
}

/// Sin los colores de la terminal (\x1b[...m) ni los ceros de los mensajes de wsl.exe (UTF-16).
fn clean(line: &[u8]) -> String {
    let text = String::from_utf8_lossy(line).replace('\0', "");
    let mut out = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\x1b' && chars.peek() == Some(&'[') {
            chars.next();
            for d in chars.by_ref() {
                if d.is_ascii_alphabetic() {
                    break;
                }
            }
        } else {
            out.push(c);
        }
    }
    out.trim().to_string()
}

/// La dirección del panel (http://127.0.0.1:PUERTO/?t=CLAVE) en una línea, si está.
fn find_url(line: &str) -> Option<String> {
    let start = line.find("http://127.0.0.1:")?;
    let url: String = line[start..]
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || ":/?=_-.".contains(*c))
        .collect();
    url.contains("/?t=").then_some(url)
}

fn port_of(url: &str) -> Option<u16> {
    url.strip_prefix("http://127.0.0.1:")?.split('/').next()?.parse().ok()
}

/// Por qué no arrancó, en palabras: lo que dijo andamio (o WSL), sin adivinar de más.
fn explain(said: &[String]) -> String {
    let all = said.join("\n");
    let low = all.to_lowercase();
    if low.contains("andamio: command not found") || low.contains("andamio: not found") || low.contains("command not found: andamio") {
        let (es, en) = where_andamio();
        return l(
            &format!("No encontré el comando andamio{es}. Instálalo (bin/andamio setup, en tu copia) y vuelve a intentar."),
            &format!("I couldn't find the andamio command{en}. Install it (bin/andamio setup, in your copy) and try again."),
        );
    }
    if low.contains("no installed distributions") || low.contains("no tiene distribuciones") {
        return l(
            "WSL no tiene ninguna distribución de Linux instalada. Instala Ubuntu (wsl --install -d Ubuntu) y andamio en ella.",
            "WSL has no Linux distribution installed. Install Ubuntu (wsl --install -d Ubuntu) and andamio in it.",
        );
    }
    let last: Vec<&str> = said.iter().rev().filter(|s| !s.is_empty()).take(8).map(String::as_str).collect();
    let tail = last.into_iter().rev().collect::<Vec<_>>().join("\n");
    if tail.is_empty() {
        l("El panel no arrancó y no dijo por qué.", "The panel didn't start and didn't say why.")
    } else {
        format!("{}\n\n{}", l("El panel no arrancó. Lo último que dijo:", "The panel didn't start. The last thing it said:"), tail)
    }
}

/// Arranca el panel y devuelve su dirección cuando ya se puede abrir desde aquí.
fn launch(app: &AppHandle) -> Result<String, String> {
    let mut child = panel_command()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| {
            if cfg!(windows) && e.kind() == std::io::ErrorKind::NotFound {
                l(
                    "No encontré WSL en este Windows. andamio corre dentro de WSL: instálalo (wsl --install) y vuelve a intentar.",
                    "I couldn't find WSL on this Windows. andamio runs inside WSL: install it (wsl --install) and try again.",
                )
            } else {
                format!("{} {e}", l("No pude arrancar el panel:", "Couldn't start the panel:"))
            }
        })?;
    let stdout = child.stdout.take().ok_or("stdout")?;
    let stderr = child.stderr.take().ok_or("stderr")?;
    let state = app.state::<Panel>();
    *state.stdin.lock().unwrap() = child.stdin.take();

    // Lo que dice por stderr, para explicar un error (las últimas líneas).
    let said = Arc::new(Mutex::new(Vec::<String>::new()));
    let said_err = Arc::clone(&said);
    thread::spawn(move || {
        let mut reader = BufReader::new(stderr);
        let mut buf = Vec::new();
        while reader.read_until(b'\n', &mut buf).map(|n| n > 0).unwrap_or(false) {
            let mut s = said_err.lock().unwrap();
            s.push(clean(&buf));
            if s.len() > 40 {
                s.remove(0);
            }
            buf.clear();
        }
    });

    let mut reader = BufReader::new(stdout);
    let mut buf = Vec::new();
    loop {
        buf.clear();
        match reader.read_until(b'\n', &mut buf) {
            Ok(0) | Err(_) => break,
            Ok(_) => {
                let line = clean(&buf);
                if let Some(url) = find_url(&line) {
                    // Lo demás que imprima se lee y se descarta: si nadie lo lee, el panel se trabaría.
                    thread::spawn(move || {
                        let mut sink = Vec::new();
                        while reader.read_until(b'\n', &mut sink).map(|n| n > 0).unwrap_or(false) {
                            sink.clear();
                        }
                    });
                    *state.child.lock().unwrap() = Some(child);
                    wait_reachable(&url)?;
                    return Ok(url);
                }
                said.lock().unwrap().push(line);
            }
        }
    }
    let _ = child.wait();
    *state.stdin.lock().unwrap() = None;
    let said = said.lock().unwrap().clone();
    Err(explain(&said))
}

/// Esperar a que el panel responda. En Windows corre en WSL: su 127.0.0.1 llega aquí por el reenvío de WSL.
fn wait_reachable(url: &str) -> Result<(), String> {
    let port = port_of(url).ok_or_else(|| l("Dirección del panel inválida", "Invalid panel address"))?;
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        if TcpStream::connect_timeout(&addr, Duration::from_millis(500)).is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(250));
    }
    if !cfg!(windows) {
        return Err(l(
            &format!("El panel arrancó, pero no responde en 127.0.0.1:{port}."),
            &format!("The panel started, but it doesn't answer on 127.0.0.1:{port}."),
        ));
    }
    Err(l(
        &format!("El panel arrancó en WSL, pero Windows no llega a 127.0.0.1:{port}. Revisa que WSL reenvíe localhost (localhostForwarding en .wslconfig)."),
        &format!("The panel started in WSL, but Windows can't reach 127.0.0.1:{port}. Check that WSL forwards localhost (localhostForwarding in .wslconfig)."),
    ))
}

/// Arranca el panel en otro hilo y, cuando está, lleva la ventana a él (o deja el error a la vista).
fn start_panel(app: AppHandle) {
    thread::spawn(move || {
        *app.state::<Panel>().error.lock().unwrap() = None;
        match launch(&app) {
            Ok(url) => match (app.get_webview_window("main"), Url::parse(&url)) {
                (Some(w), Ok(u)) => {
                    *app.state::<Panel>().url.lock().unwrap() = Some(url.clone());
                    // Si se está actualizando, la ventana sigue en la página de la actualización.
                    if app.state::<Panel>().update_phase.lock().unwrap().is_none() {
                        let _ = w.navigate(u);
                    }
                }
                _ => *app.state::<Panel>().error.lock().unwrap() = Some(l("No pude abrir el panel.", "Couldn't open the panel.")),
            },
            Err(msg) => *app.state::<Panel>().error.lock().unwrap() = Some(msg),
        }
    });
}

/// Cierra la entrada del panel (se apaga solo) y, si en 5 s no terminó, lo corta.
fn stop_panel(app: &AppHandle) {
    let state = app.state::<Panel>();
    drop(state.stdin.lock().unwrap().take());
    // Se saca del candado antes de esperar: mientras espera, el candado queda libre.
    let child = state.child.lock().unwrap().take();
    if let Some(mut child) = child {
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline {
            if let Ok(Some(_)) = child.try_wait() {
                return;
            }
            thread::sleep(Duration::from_millis(100));
        }
        let _ = child.kill();
    }
}

/// Para la página de arranque: el error, si lo hubo (None mientras arranca).
#[tauri::command]
fn startup_error(state: tauri::State<'_, Panel>) -> Option<String> {
    state.error.lock().unwrap().clone()
}

/// "Reintentar" en la página de arranque.
#[tauri::command]
fn retry(app: AppHandle) {
    stop_panel(&app);
    start_panel(app);
}

/// Para la página de la actualización: fase (downloading, installing), bytes y error.
#[tauri::command]
fn update_status(state: tauri::State<'_, Panel>) -> serde_json::Value {
    serde_json::json!({
        "phase": state.update_phase.lock().unwrap().clone(),
        "done": state.update_done.load(Ordering::Relaxed),
        "total": state.update_total.load(Ordering::Relaxed),
        "error": state.update_error.lock().unwrap().clone(),
    })
}

/// "Volver al panel" después de una actualización que falló.
#[tauri::command]
fn back_to_panel(app: AppHandle) {
    let state = app.state::<Panel>();
    *state.update_phase.lock().unwrap() = None;
    *state.update_error.lock().unwrap() = None;
    let url = state.url.lock().unwrap().clone();
    let running = state.child.lock().unwrap().is_some();
    match (url, running, app.get_webview_window("main")) {
        (Some(u), true, Some(w)) => {
            if let Ok(u) = Url::parse(&u) {
                let _ = w.navigate(u);
            }
        }
        (_, _, Some(w)) => {
            // El panel ya se había apagado para instalar: se arranca de nuevo.
            if let Some(u) = local_page("") {
                let _ = w.navigate(u);
            }
            start_panel(app.clone());
        }
        _ => {}
    }
}

/// Los textos de la página de arranque, en el idioma del sistema.
#[tauri::command]
fn texts() -> serde_json::Value {
    serde_json::json!({
        "starting": l("Arrancando el panel…", "Starting the panel…"),
        "hint": l("andamio corre en tu máquina y habla con tu servidor por SSH.", "andamio runs on your machine and talks to your server over SSH."),
        "slow": l("Está tardando: puede que tu servidor tarde en responder por SSH.", "It's taking a while: your server may be slow to answer over SSH."),
        "failed": l("No se pudo abrir el panel", "Couldn't open the panel"),
        "retry": l("Reintentar", "Try again"),
        "updating": l("Actualizando andamio de escritorio", "Updating andamio desktop"),
        "downloading": l("Descargando la versión nueva…", "Downloading the new version…"),
        "installing": l("Instalando… la app se cierra y se vuelve a abrir sola.", "Installing… the app closes and opens again by itself."),
        "updateFailed": l("No se pudo actualizar", "Couldn't update"),
        "back": l("Volver al panel", "Back to the panel"),
    })
}

/// ¿Hay una versión nueva (firmada con la llave de andamio)? Si sí, pregunta antes de instalarla.
async fn check_update(app: AppHandle) -> Result<(), String> {
    let found = match app.updater() {
        Ok(u) => u.check().await,
        Err(e) => Err(e),
    };
    let update = match found {
        Ok(Some(u)) => u,
        Ok(None) => return Ok(()),
        Err(e) => {
            log(&app, &format!("update: no pude buscar versiones nuevas: {e}"));
            return Err(e.to_string());
        }
    };
    let msg = l(
        &format!("Hay una versión nueva de andamio de escritorio: {} (tienes la {}).\n\nSe descarga, se instala y la app se reinicia. Tu servidor y tu configuración no se tocan.", update.version, update.current_version),
        &format!("There's a new version of andamio desktop: {} (you have {}).\n\nIt downloads, installs and the app restarts. Your server and your configuration aren't touched.", update.version, update.current_version),
    );
    let ask = app.clone();
    let yes = tauri::async_runtime::spawn_blocking(move || {
        ask.dialog()
            .message(msg)
            .title(l("Actualización disponible", "Update available"))
            .kind(MessageDialogKind::Info)
            .buttons(MessageDialogButtons::OkCancelCustom(l("Actualizar y reiniciar", "Update and restart"), l("Después", "Later")))
            .blocking_show()
    })
    .await
    .map_err(|e| e.to_string())?;
    if !yes {
        log(&app, &format!("update {}: después", update.version));
        return Ok(());
    }
    log(&app, &format!("update {}: descargando {}", update.version, update.download_url));
    let state = app.state::<Panel>();
    *state.update_error.lock().unwrap() = None;
    state.update_done.store(0, Ordering::Relaxed);
    state.update_total.store(0, Ordering::Relaxed);
    *state.update_phase.lock().unwrap() = Some("downloading".into());
    if let (Some(w), Some(u)) = (app.get_webview_window("main"), local_page("#update")) {
        let _ = w.navigate(u);
    }
    let progress = app.clone();
    let bytes = match update
        .download(
            move |chunk, total| {
                let s = progress.state::<Panel>();
                s.update_done.fetch_add(chunk as u64, Ordering::Relaxed);
                if let Some(t) = total {
                    s.update_total.store(t, Ordering::Relaxed);
                }
            },
            || {},
        )
        .await
    {
        Ok(b) => b,
        Err(e) => return Err(fail(&app, &format!("{} {e}", l("La descarga falló:", "The download failed:")))),
    };
    log(&app, &format!("update {}: descargado ({} bytes, firma verificada); instalando", update.version, bytes.len()));
    *state.update_phase.lock().unwrap() = Some("installing".into());
    // El instalador reemplaza la app: el panel se apaga limpio antes.
    stop_panel(&app);
    if let Err(e) = update.install(bytes) {
        return Err(fail(&app, &format!("{} {e}", l("La instalación falló:", "The installation failed:"))));
    }
    log(&app, &format!("update {}: instalado, reiniciando", update.version));
    app.restart();
}

/// Una actualización que falló: queda en el registro y a la vista (con "Volver al panel").
fn fail(app: &AppHandle, msg: &str) -> String {
    log(app, &format!("update: {msg}"));
    *app.state::<Panel>().update_error.lock().unwrap() = Some(msg.to_string());
    msg.to_string()
}

/// Dentro de la ventana: los links de afuera (target=_blank, window.open) navegan aquí mismo, y
/// on_navigation los manda a tu navegador.
const INIT: &str = r#"
(() => {
  if (!/^(127\.0\.0\.1|localhost)$/.test(location.hostname)) return;
  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || a.target !== "_blank") return;
    const u = new URL(a.href, location.href);
    if (u.origin === location.origin) return;
    e.preventDefault();
    location.href = u.href;
  }, true);
  const open = window.open;
  window.open = (u, ...rest) => {
    try {
      const x = new URL(String(u), location.href);
      if (x.origin !== location.origin) { location.href = x.href; return null; }
    } catch (_) {}
    return open.call(window, u, ...rest);
  };
})();
"#;

/// Lo que se queda en la ventana: la página de arranque y los paneles de andamio (127.0.0.1).
fn stays_inside(url: &Url) -> bool {
    match (url.scheme(), url.host_str()) {
        ("tauri", _) | ("about", _) => true,
        ("http", Some("tauri.localhost")) | ("https", Some("tauri.localhost")) => true,
        ("http", Some("127.0.0.1")) | ("http", Some("localhost")) => true,
        _ => false,
    }
}

fn main() {
    tauri::Builder::default()
        // Una sola ventana: abrirla otra vez trae al frente la que ya está.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Panel::default())
        .invoke_handler(tauri::generate_handler![startup_error, retry, texts, update_status, back_to_panel])
        .setup(|app| {
            let handle = app.handle().clone();
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("andamio")
                .inner_size(1320.0, 860.0)
                .min_inner_size(820.0, 560.0)
                .initialization_script(INIT)
                .on_navigation(move |url| {
                    if stays_inside(url) {
                        return true;
                    }
                    if matches!(url.scheme(), "http" | "https" | "mailto") {
                        let _ = handle.opener().open_url(url.as_str(), None::<&str>);
                    }
                    false
                })
                .build()?;
            start_panel(app.handle().clone());
            let updates = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let _ = check_update(updates).await;
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("andamio de escritorio no pudo arrancar")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_panel(app);
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_the_panel_address() {
        let line = clean(b"\n  \x1b[1mhttp://127.0.0.1:41234/?t=AbC_d-9\x1b[0m\n");
        assert_eq!(find_url(&line).as_deref(), Some("http://127.0.0.1:41234/?t=AbC_d-9"));
        assert_eq!(port_of("http://127.0.0.1:41234/?t=x"), Some(41234));
        assert_eq!(find_url("Panel de andamio"), None);
        assert_eq!(find_url("http://127.0.0.1:80/"), None, "sin clave no es el panel");
    }

    #[test]
    fn utf16_from_wsl_is_readable() {
        let raw = "W\0S\0L\0 \0e\0r\0r\0o\0r\0".as_bytes();
        assert_eq!(clean(raw), "WSL error");
    }

    #[test]
    fn only_local_pages_stay_inside() {
        for (u, inside) in [
            ("http://127.0.0.1:41234/?t=x", true),
            ("http://localhost:5000/", true),
            ("http://tauri.localhost/index.html", true),
            ("tauri://localhost/index.html", true),
            ("https://github.com/andamio-me/andamio", false),
            ("https://api.example.com/api", false),
            ("http://127.0.0.2:80/", false),
        ] {
            assert_eq!(stays_inside(&Url::parse(u).unwrap()), inside, "{u}");
        }
    }
}
