# Lecciones aprendidas

[English](lessons-learned.md) · **Español**

Todos los incidentes reales encontrados al construir este proyecto: qué se rompió, por qué y qué
cambió para que no se repita. Los seis que más enseñan están también en una
[infografía](diagrams/es/05-incidents.png).

Están en el orden en que ocurrieron.

| # | Problema | Causa | Solución |
|---|---|---|---|
| 1  `docker build` falla con **429 Too Many Requests** | Límite de descargas anónimas de Docker Hub | Usar un mirror (`mirror.gcr.io`) para la imagen base |
| 2  `pip` falla dentro del build: *certificate verify failed* | Un proxy corporativo intercepta HTTPS | Inyectar la CA del proxy **solo** en una etapa de build local, nunca en la imagen final |
| 3  `trivy-action` falla al instalar Trivy | El script de instalación no podía descargar el binario | Ejecutar la imagen oficial de Trivy **fijada por digest** (además, más seguro) |
| 4  El rolling update falla: *annotations: expected string* | El chart no convertía a texto anotaciones numéricas | `quote` en la plantilla; lo detectó el test E2E en k3s |
| 5  En `main` fallan Trivy y Cosign: *could not parse reference* | `github.repository` conserva mayúsculas (`EA-etn`) y Docker exige minúsculas | Normalizar con `${IMAGE,,}`. Los pasos que solo corren en `main` también necesitan cobertura |
| 6  Una release no ejecuta el pipeline | El commit del tag contenía la marca para **omitir CI**; GitHub también la lee del título del PR en el commit de merge | Quitar la marca del commit del bot (los push con `GITHUB_TOKEN` no disparan workflows) y no usarla en títulos de PR |
| 7  `main` falla justo después de un merge: Trivy encuentra una **CVE HIGH nueva** en `apt` | Se publicó horas después de que pasara el PR; la imagen base oficial aún no tenía el parche | `apt-get upgrade` en la etapa final. La puerta funcionó: la imagen no se firmó ni se desplegó |
| 8  El bot de GitOps no puede hacer push: `GH013 Repository rule violations` | El ruleset de `main` exige checks y `GITHUB_TOKEN` no puede saltárselo | El bot empuja con una **deploy key** SSH incluida en el bypass del ruleset; `paths-ignore` evita que su commit relance el pipeline |
| 9  Los pods terminan en `Error` al apagarse durante un rolling update | Uvicorn ≥ 0.29 relanza `SIGTERM` tras un apagado limpio: código de salida 143 | `app/serve.py` sale con 0, y un `preStop` con espera para que el Ingress deje de enviar tráfico antes. El CI demuestra 0 peticiones fallidas durante un despliegue |
| 10  El arreglo pasó el CI y Docker en local, pero en el homelab los pods seguían en `Error` (código 1) | Uvicorn relanza la señal con `signal.raise_signal()` y la política de seguridad del nodo (probablemente AppArmor) lo prohíbe: `PermissionError` | Una subclase de `uvicorn.Server` que no relanza la señal. Un test simula ahora esa restricción. Lección: el CI no es producción; mira el código de salida y los logs reales |
| 11  `main` y los PR fallan días después: Trivy encuentra **CVE HIGH nuevas** en `zlib` aunque la imagen ejecuta `apt-get upgrade` | La caché de BuildKit en GitHub Actions reutilizaba la capa antigua de `apt-get upgrade`: el comando no cambiaba, así que los parches nunca llegaban | El CI pasa la fecha del día como argumento de build (`APT_CACHE_BUST`) y esa capa se rehace al menos una vez al día. Una caché necesita caducidad |
| 12  Tras cada despliegue, **las dos réplicas acaban en el mismo nodo** aunque los dos están sanos | La regla de reparto (`ScheduleAnyway`) también contaba los pods viejos que estaban a punto de apagarse, así que los nuevos parecían repartidos aunque caían en el mismo nodo | `matchLabelKeys: [pod-template-hash]`: solo se cuentan los pods de la misma versión. Detectado en el homelab con `/info`, tras descartar primero un problema en la Pi (`Ready`, sin taints ni presión) |
| 13  Tras reiniciar el portátil (worker), **las dos réplicas se quedaron en la Raspberry Pi** | Kubernetes desalojó el pod del nodo inalcanzable a los ~5 min y lo recreó en la Pi; cuando el nodo volvió nadie lo movió, porque el planificador solo coloca los pods al crearlos, y la regla de reparto era solo una preferencia | En el homelab la regla es obligatoria (`DoNotSchedule`) con `nodeTaintsPolicy: Honor`, para que un nodo caído no bloquee los pods nuevos. Después, el [Descheduler](https://github.com/EA-etn/homelab-k3s/blob/main/apps/descheduler.yaml) devuelve un pod a su nodo en menos de 5 minutos desde que vuelve |

## Qué tienen en común

- **Una comprobación que solo corre en un sitio es un punto ciego.** Tres incidentes (#5, #6, #10)
  pasaron todos los pull requests y fallaron en `main`, en un tag de versión o en el clúster real.
- **Las puertas de seguridad se ganan el sueldo después del merge.** Dos veces (#7, #11) apareció
  una CVE en código que no había cambiado. Las dos veces la imagen ni se firmó ni se desplegó.
- **Los valores por defecto son opiniones.** Una caché que nunca caduca (#11), una regla de reparto
  que solo es una preferencia (#12, #13): cada valor por defecto era razonable hasta que dejó de serlo.
