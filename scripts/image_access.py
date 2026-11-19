#!/usr/bin/env python3
"""Local secret dialog, shared image profile, and bundled imagegen CLI launcher.

No image API implementation lives here. Secrets go only to the OS credential
store and the imagegen child environment; subprocess output is never echoed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import uuid

MODEL = "gpt-image-2"
SERVICE = "Codex-Shared-Image-API"
OFFICIAL_URL = "https://api.openai.com/v1"
SKILL = Path(__file__).resolve().parents[1]


class AccessError(Exception):
    pass


def codex_home():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def profile_path():
    return codex_home() / "image-api" / "config.json"


def normalize_url(value):
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        raise AccessError("base_url 地址或端口无效。") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or any(c.isspace() for c in value)):
        raise AccessError("base_url 必须是 HTTPS API 根地址，不能包含密钥、用户名、查询参数或片段。")
    return value


def backend():
    if platform.system() == "Darwin" and Path("/usr/bin/security").exists():
        return "macOS-Keychain"
    if platform.system() == "Linux" and shutil.which("secret-tool"):
        return "Secret-Service"
    raise AccessError("当前系统没有受支持的凭据库；macOS 需 Keychain，Linux 需 secret-tool 和已解锁的 Secret Service。未保存密钥。")


def credential(profile, operation, key=None):
    store = profile["credential_storage"]
    service, account = profile["credential_service"], profile["credential_account"]
    if store == "macOS-Keychain":
        if operation == "set":
            # security's interactive parser reads stdin; key is absent from argv.
            words = ["add-generic-password", "-U", "-s", service, "-a", account, "-w", key]
            cmd = ["/usr/bin/security", "-i"]
            data = " ".join(shlex.quote(w) for w in words) + "\n"
        else:
            cmd = ["/usr/bin/security", "find-generic-password" if operation == "get"
                   else "delete-generic-password", "-s", service, "-a", account]
            if operation == "get":
                cmd.append("-w")
            data = None
    elif store == "Secret-Service":
        cmd = ["secret-tool", {"set": "store", "get": "lookup", "delete": "clear"}[operation]]
        if operation == "set":
            cmd += ["--label=Codex shared image API"]
        cmd += ["service", service, "account", account]
        data = key if operation == "set" else None
    else:
        raise AccessError("不支持此凭据库；请重新配置。")
    try:
        result = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        raise AccessError("凭据库不可访问或操作超时；现有配置未替换。") from None
    if result.returncode:
        raise AccessError("凭据库操作失败；请检查本机权限或解锁状态。")
    if operation == "get":
        value = result.stdout.rstrip("\r\n")
        if not value:
            raise AccessError("已保存的凭据为空；请重新配置。")
        return value


def load_profile():
    try:
        p = json.loads(profile_path().read_text(encoding="utf-8"))
        if p["model"] != MODEL or p.get("api_authorized") is not True:
            raise ValueError()
        p["base_url"] = normalize_url(p["base_url"])
        for name in ("credential_storage", "credential_service", "credential_account"):
            if not isinstance(p[name], str) or not p[name]:
                raise ValueError()
        return p
    except FileNotFoundError:
        raise AccessError("尚无共享生图配置；需先选择配置 API。") from None
    except (ValueError, KeyError, TypeError):
        raise AccessError("共享生图配置无效；请重新配置。") from None


def save_profile(p):
    path = profile_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.chmod(name, 0o600)
            json.dump(p, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def dialog(default_url):
    if platform.system() == "Darwin":
        script = '''
const app = Application.currentApplication();
app.includeStandardAdditions = true;
try {
  const key = app.displayDialog("请输入用于 gpt-image-2 的 API key（不会发送到聊天）。若使用中转站，下一窗口还需填写其 base URL。", {defaultAnswer:"", hiddenAnswer:true, withTitle:"Codex 生图全局配置", buttons:["取消","下一步"], defaultButton:"下一步", cancelButton:"取消"}).textReturned;
  const url = app.displayDialog("请输入 API base URL。官方默认 https://api.openai.com/v1；使用中转站时，请填该站的 API 根地址（通常以 /v1 结尾）。密钥和必要图片将提交至该地址。", {defaultAnswer:DEFAULT_URL, withTitle:"Codex 生图全局配置", buttons:["取消","测试并保存"], defaultButton:"测试并保存", cancelButton:"取消"}).textReturned;
  JSON.stringify({key:key, base_url:url});
} catch (e) { JSON.stringify({cancelled:true}); }
'''.replace("DEFAULT_URL", json.dumps(default_url))
        try:
            r = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript"], input=script,
                               capture_output=True, text=True, timeout=600)
            if r.returncode:
                raise AccessError("无法打开本机密钥窗口；请在本机桌面环境运行 configure。")
            answer = json.loads(r.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise AccessError("本机密钥窗口未完成；未保存配置。") from None
    else:
        try:
            import tkinter as tk
            root = tk.Tk()
            root.title("Codex 生图全局配置")
            answer = {"cancelled": True}
            tk.Label(root, text="API key（隐藏输入，不会发送到聊天）").pack(padx=20, pady=(15, 4))
            key_entry = tk.Entry(root, width=54, show="*")
            key_entry.pack(padx=20)
            tk.Label(root, text="API base URL：中转站用户必须填写其 API 根地址\n密钥和必要图片将提交至此地址。").pack(padx=20, pady=(12, 4))
            url_entry = tk.Entry(root, width=54)
            url_entry.insert(0, default_url)
            url_entry.pack(padx=20)
            def submit():
                answer.update(key=key_entry.get(), base_url=url_entry.get(), cancelled=False)
                root.destroy()
            tk.Button(root, text="测试并保存", command=submit).pack(pady=15)
            key_entry.focus_set()
            root.mainloop()
        except Exception:
            # No exception text is printed: GUI implementations may include input.
            raise AccessError("无法打开本机密钥窗口；请在有桌面的本机运行 configure 并检查 tkinter。") from None
    if answer.get("cancelled"):
        raise AccessError("用户已取消；未测试或替换现有配置。")
    key = answer["key"].strip()
    if not key or any(c.isspace() for c in key):
        raise AccessError("API key 为空或包含空白；未测试或保存。")
    return key, normalize_url(answer["base_url"])


def bundled_cli():
    path = codex_home() / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"
    if not path.is_file():
        raise AccessError("未找到当前环境的 imagegen CLI；请先定位或安装该技能。")
    return path


def child_run(p, key, args, timeout=600):
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = key
    env["OPENAI_BASE_URL"] = p["base_url"]
    # Do not leak unrelated chat-provider organization/project headers.
    env.pop("OPENAI_ORG_ID", None)
    env.pop("OPENAI_PROJECT_ID", None)
    try:
        result = subprocess.run([sys.executable, str(bundled_cli()), *args],
                                env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AccessError("生图请求超时；未判定可用，请检查网络或服务状态后再试。") from None
    if result.returncode:
        message = (result.stderr + result.stdout).lower()
        if "401" in message or "invalid_api_key" in message:
            reason = "认证失败（401）；请检查密钥及对应的 base URL。"
        elif "403" in message:
            reason = "访问被拒绝（403）；请检查模型权限或组织验证。"
        elif "429" in message or "quota" in message:
            reason = "额度不足或限流；请检查账户额度并稍后重试。"
        elif "model" in message and ("not found" in message or "404" in message):
            reason = "该服务未提供所请求的 gpt-image-2 模型。"
        elif "no module named" in message:
            reason = "当前 Python 缺少 imagegen CLI 依赖；请检查 openai 和 Pillow。"
        else:
            reason = "生图请求失败；请检查网络、模型与图像编辑接口支持。"
        raise AccessError(reason + " 已隐藏可能含凭据的原始响应。")


def probe(p, key, output_dir):
    from PIL import Image
    output_dir.mkdir(parents=True, exist_ok=True)
    output = (output_dir / ("probe-" + uuid.uuid4().hex + ".png")).resolve()
    reference = SKILL / "assets" / "references" / "b-method.png"
    if not reference.is_file():
        raise AccessError("缺少测试参考图片；未发送请求。")
    child_run(p, key, ["edit", "--model", MODEL, "--image", str(reference),
                      "--prompt", "Diagnostic image only. Using the supplied slide as visual reference, create a white square with two blue rectangles connected by one blue arrow. No text or logos.",
                      "--size", "1024x1024", "--quality", "low", "--no-augment",
                      "--out", str(output)], timeout=180)
    try:
        with Image.open(output) as img:
            img.load()
            size = list(img.size)
            if min(size) < 1:
                raise ValueError()
    except (OSError, ValueError):
        raise AccessError("接口未返回可解码图片，测试未通过；未替换全局配置。") from None
    report = {"status": "passed", "tool": "imagegen-cli", "model_requested": MODEL,
              "backend_verified": False, "reference_input_tested": True,
              "image": str(output), "size": size,
              "tested_at": datetime.now(timezone.utc).isoformat()}
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="只检查共享配置是否存在；不会读取或打印密钥，不等于生图通过")
    for name in ("configure", "probe"):
        s = sub.add_parser(name)
        s.add_argument("--output-dir", type=Path, required=True)
    runner = sub.add_parser("run", help="从全局凭据库向子进程注入环境，直接调用原版 imagegen CLI")
    runner.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "status":
            p = load_profile()
            result = {"configured": True, "config_path": str(profile_path()),
                      "model": p["model"], "credential_storage": p["credential_storage"],
                      "preflight_passed": False}
        elif args.action == "configure":
            store = backend()
            # Catch dependency failures before prompting for secrets or billing.
            import openai
            import PIL
            bundled_cli()
            try:
                default = load_profile()["base_url"]
            except AccessError:
                default = OFFICIAL_URL
            key, url = dialog(default)
            p = {"version": 1, "base_url": url, "model": MODEL, "api_authorized": True,
                 "credential_storage": store, "credential_service": SERVICE,
                 "credential_account": "image-generation-" + uuid.uuid4().hex}
            result = probe(p, key, args.output_dir)
            credential(p, "set", key)
            try:
                # Verify the store round trip before publishing the profile.
                if credential(p, "get") != key:
                    raise AccessError("凭据库回读校验失败；未替换全局配置。")
                p["validated_at"] = result["tested_at"]
                save_profile(p)
            except Exception:
                credential(p, "delete")
                raise
            result.update(global_config_saved=True, config_path=str(profile_path()))
        else:
            p = load_profile()
            key = credential(p, "get")
            if args.action == "probe":
                result = probe(p, key, args.output_dir)
            else:
                cli_args = args.cli_args
                if cli_args and cli_args[0] == "--":
                    cli_args = cli_args[1:]
                if not cli_args or cli_args[0] not in {"edit", "generate", "generate-batch"}:
                    raise AccessError("run 后须提供原版 CLI 的 edit、generate 或 generate-batch 子命令。")
                # Bundle's default model may change; make the requested model explicit.
                if any(a == "--model" or a.startswith("--model=") for a in cli_args):
                    raise AccessError("此启动器固定请求 gpt-image-2，请移除重复的 --model 参数。")
                if cli_args[0] == "generate-batch":
                    raise AccessError("此启动器请逐页使用 edit，以实际传入风格参考；不接受可能覆盖模型的批量任务。")
                child_run(p, key, [cli_args[0], "--model", MODEL, *cli_args[1:]], timeout=1800)
                result = {"status": "completed", "model_requested": MODEL,
                          "backend_verified": False, "note": "仍须检查输出图片与学术内容。"}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AccessError, OSError, ImportError) as exc:
        message = str(exc) if isinstance(exc, AccessError) else "依赖或本机文件访问失败；未完成配置/生图。"
        print(json.dumps({"status": "failed", "message": message}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
