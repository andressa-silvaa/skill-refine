from __future__ import annotations

from html import escape

BRAND_NAME = "Skill Refine"
COLOR_PRIMARY = "#c72cb8"
COLOR_TEXT = "#1e1a1d"
COLOR_MUTED = "#775f73"
COLOR_BG = "#f6e6f4"
COLOR_CARD = "#ffffff"
COLOR_BORDER = "#f1c3ea"


def _normalize_frontend_url(frontend_url: str | None) -> str | None:
    url = (frontend_url or "").strip()
    if not url:
        return None
    return url[:-1] if url.endswith("/") else url


def _button_html(*, href: str, label: str) -> str:
    href_e = escape(href, quote=True)
    label_e = escape(label)
    return f"""
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{href_e}" style="height:44px;v-text-anchor:middle;width:260px;" arcsize="20%" strokecolor="{COLOR_PRIMARY}" fillcolor="{COLOR_PRIMARY}">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial, Helvetica, sans-serif;font-size:14px;font-weight:bold;">
          {label_e}
        </center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-- -->
      <a href="{href_e}"
         style="display:inline-block;background-color:{COLOR_PRIMARY};color:#ffffff;text-decoration:none;font-family:Arial, Helvetica, sans-serif;font-size:14px;font-weight:bold;line-height:44px;text-align:center;width:260px;border-radius:10px;mso-line-height-rule:exactly;">
        {label_e}
      </a>
      <!--<![endif]-->
    """.strip()


def render_base_email(
    *,
    preheader: str,
    title: str,
    paragraphs: list[str],
    cta_label: str | None = None,
    cta_url: str | None = None,
    extra_block_html: str | None = None,
) -> str:
    preheader_e = escape(preheader)
    title_e = escape(title)
    paragraphs_html = "\n".join(
        f'<p style="margin:0 0 12px 0;font-family:Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;color:{COLOR_TEXT};mso-line-height-rule:exactly;">{escape(p)}</p>'
        for p in paragraphs
    )

    cta_html = ""
    if cta_label and cta_url:
        cta_html = f"""
          <tr>
            <td align="center" style="padding:18px 0 6px 0;">
              {_button_html(href=cta_url, label=cta_label)}
            </td>
          </tr>
        """.strip()

    extra_html = extra_block_html or ""

    return f"""<!doctype html>
<html lang="pt-BR" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <title>{title_e}</title>
    <!--[if mso]>
      <xml>
        <o:OfficeDocumentSettings>
          <o:AllowPNG/>
          <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
      </xml>
    <![endif]-->
  </head>
  <body style="margin:0;padding:0;background-color:{COLOR_BG};-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
    <!-- Preheader (hidden) -->
    <div style="display:none;font-size:1px;color:{COLOR_BG};line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
      {preheader_e}
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{COLOR_BG}" style="background-color:{COLOR_BG};padding:0;margin:0;border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <!--[if (gte mso 9)|(IE)]>
          <table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
            <tr>
              <td>
          <![endif]-->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;">
            <!-- Header -->
            <tr>
              <td align="left" style="padding:0 0 12px 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;">
                  <tr>
                    <td align="left" style="padding:0;">
                      <span style="font-family:Arial, Helvetica, sans-serif;font-size:22px;font-weight:bold;color:{COLOR_TEXT};">
                        Skill<span style="color:{COLOR_PRIMARY};"> Refine</span>
                      </span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Card -->
            <tr>
              <td style="padding:0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{COLOR_CARD}" style="width:100%;background-color:{COLOR_CARD};border:1px solid {COLOR_BORDER};border-radius:14px;border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;">
                  <tr>
                    <td style="padding:22px 20px;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;">
                  <tr>
                    <td align="left" style="padding:0 0 8px 0;">
                      <h1 style="margin:0;font-family:Arial, Helvetica, sans-serif;font-size:18px;line-height:24px;color:{COLOR_TEXT};">
                        {title_e}
                      </h1>
                    </td>
                  </tr>
                  <tr>
                    <td align="left" style="padding:0;">
                      {paragraphs_html}
                    </td>
                  </tr>

                  {extra_html}

                  {cta_html}

                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td align="left" style="padding:14px 4px 0 4px;">
                <p style="margin:0 0 8px 0;font-family:Arial, Helvetica, sans-serif;font-size:12px;line-height:16px;color:{COLOR_MUTED};">
                  Se você não solicitou isso, ignore este e-mail.
                </p>
                <p style="margin:0;font-family:Arial, Helvetica, sans-serif;font-size:12px;line-height:16px;color:{COLOR_MUTED};">
                  {BRAND_NAME}
                </p>
              </td>
            </tr>
          </table>
          <!--[if (gte mso 9)|(IE)]>
              </td>
            </tr>
          </table>
          <![endif]-->
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def render_email_confirmation(*, confirm_url: str, frontend_url: str | None = None) -> tuple[str, str, str]:
    subject = "Confirme seu e-mail"
    html = render_base_email(
        preheader="Confirme seu e-mail para ativar sua conta.",
        title="Confirme seu e-mail",
        paragraphs=[
            "Para concluir seu cadastro, confirme seu e-mail clicando no botão abaixo.",
            "Isso ajuda a manter sua conta segura.",
        ],
        cta_label="Confirmar e-mail",
        cta_url=confirm_url,
    )
    fe = _normalize_frontend_url(frontend_url)
    text_lines = [
        "Confirme seu e-mail",
        "",
        "Para ativar sua conta, abra este e-mail em um cliente que suporte HTML e clique em “Confirmar e-mail”.",
        "Se preferir, abra o Skill Refine e solicite um novo e-mail de confirmação.",
        "",
        "Se você não solicitou isso, ignore este e-mail.",
        BRAND_NAME,
    ]
    if fe:
        text_lines.insert(4, f"Abrir Skill Refine: {fe}/verify-email")
    text = "\n".join(text_lines)
    return subject, html, text


def render_data_export_requested(*, frontend_url: str | None = None) -> tuple[str, str, str]:
    subject = "Recebemos sua solicitação de exportação"
    html = render_base_email(
        preheader="Estamos preparando seus dados para exportação.",
        title="Exportação de dados",
        paragraphs=[
            "Recebemos sua solicitação de exportação dos seus dados.",
            "Estamos preparando os arquivos e você receberá um novo e-mail quando estiver pronto.",
        ],
        cta_label="Abrir Skill Refine" if _normalize_frontend_url(frontend_url) else None,
        cta_url=f"{_normalize_frontend_url(frontend_url)}/protected/settings" if _normalize_frontend_url(frontend_url) else None,
    )
    fe = _normalize_frontend_url(frontend_url)
    text_lines = [
        "Exportação de dados",
        "",
        "Recebemos sua solicitação de exportação dos seus dados.",
        "Estamos preparando os arquivos e você receberá um novo e-mail quando estiver pronto.",
        "",
        BRAND_NAME,
    ]
    if fe:
        text_lines.insert(4, f"Acompanhar: {fe}/protected/settings")
    text = "\n".join(text_lines)
    return subject, html, text


def render_password_reset_code(*, code: str, frontend_url: str | None = None) -> tuple[str, str, str]:
    subject = "Seu código de redefinição de senha"

    code_e = escape(code)
    extra = f"""
      <tr>
        <td align="left" style="padding:6px 0 0 0;">
          <p style="margin:0 0 8px 0;font-family:Arial, Helvetica, sans-serif;font-size:14px;line-height:20px;color:{COLOR_TEXT};">
            Seu código:
          </p>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" bgcolor="#fbf2fa" style="width:100%;background-color:#fbf2fa;border:1px solid {COLOR_BORDER};border-radius:12px;border-collapse:separate;mso-table-lspace:0pt;mso-table-rspace:0pt;">
            <tr>
              <td align="center" style="padding:14px;">
                <span style="font-family:Arial, Helvetica, sans-serif;font-size:22px;letter-spacing:2px;font-weight:bold;color:{COLOR_TEXT};">
                  {code_e}
                </span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    """.strip()

    fe = _normalize_frontend_url(frontend_url)
    cta_url = f"{fe}/reset/email" if fe else None

    html = render_base_email(
        preheader="Use este código para redefinir sua senha.",
        title="Redefinição de senha",
        paragraphs=[
            "Você solicitou a redefinição de senha. Use o código abaixo para continuar.",
        ],
        extra_block_html=extra,
        cta_label="Abrir Skill Refine" if cta_url else None,
        cta_url=cta_url,
    )

    text_lines = [
        "Redefinição de senha",
        "",
        "Você solicitou a redefinição de senha.",
        f"Código: {code}",
        "",
        "Se você não solicitou isso, ignore este e-mail.",
        BRAND_NAME,
    ]
    if cta_url:
        text_lines.insert(4, f"Abrir: {cta_url}")
    text = "\n".join(text_lines)

    return subject, html, text


