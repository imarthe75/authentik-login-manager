import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import { Color } from '@tiptap/extension-color';
import { TextStyle } from '@tiptap/extension-text-style';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { Table } from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import Image from '@tiptap/extension-image';
import Mention from '@tiptap/extension-mention';
import { Extension } from '@tiptap/core';
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  AlignLeft, AlignCenter, AlignRight,
  List, ListOrdered, Link2, Link2Off,
  Type, Code2, Heading1, Heading2, Minus,
  RotateCcw, Highlighter, Quote, Code, Subscript, Superscript,
  Table2, ImagePlus, Rows3, Columns3, Trash2, Undo2, Redo2,
} from 'lucide-react';

export interface EmailVariable {
  var: string;
  desc: string;
}

// Autocompletado de variables: al teclear "{{" se abre una lista filtrable de
// las variables reales del catálogo (evita el typo silencioso de escribir
// {{contaco_soporte}} a mano, que se enviaría literal sin ningún aviso).
// Se implementa con DOM manual (sin ReactRenderer/tippy) para no sumar
// dependencias nuevas solo por el popup de sugerencias.
function createVariableSuggestion(variablesRef: React.MutableRefObject<EmailVariable[]>) {
  return {
    char: '{{',
    allowSpaces: false,
    items: ({ query }: { query: string }) => {
      const q = query.toLowerCase();
      return variablesRef.current
        .filter((v) => v.var.toLowerCase().includes(q))
        .slice(0, 8);
    },
    command: ({ editor, range, props }: any) => {
      const id = String(props.var).replace(/[{}]/g, '');
      editor.chain().focus().insertContentAt(range, [
        { type: 'mention', attrs: { id } },
        { type: 'text', text: ' ' },
      ]).run();
    },
    render: () => {
      let popup: HTMLDivElement | null = null;
      let selectedIndex = 0;
      let currentItems: EmailVariable[] = [];
      let currentCommand: ((item: EmailVariable) => void) | null = null;

      const renderList = () => {
        if (!popup) return;
        popup.innerHTML = '';
        if (currentItems.length === 0) {
          const empty = document.createElement('div');
          empty.textContent = 'Sin variables que coincidan';
          empty.style.cssText = 'padding:8px 10px;font-size:12px;color:#9ca3af;';
          popup.appendChild(empty);
          return;
        }
        currentItems.forEach((item, i) => {
          const row = document.createElement('div');
          row.title = item.desc;
          row.style.cssText = `padding:6px 10px;cursor:pointer;${i === selectedIndex ? 'background:#e8f0fb;' : ''}`;
          const varEl = document.createElement('div');
          varEl.textContent = item.var;
          varEl.style.cssText = 'font-family:monospace;font-size:12px;font-weight:600;color:#1d4ed8;';
          const descEl = document.createElement('div');
          descEl.textContent = item.desc;
          descEl.style.cssText = 'font-size:10px;color:#6b7280;margin-top:1px;';
          row.appendChild(varEl);
          row.appendChild(descEl);
          row.addEventListener('mousedown', (e) => {
            e.preventDefault();
            currentCommand?.(item);
          });
          popup!.appendChild(row);
        });
      };

      const position = (clientRect?: (() => DOMRect | null) | null) => {
        const rect = clientRect?.();
        if (rect && popup) {
          popup.style.left = `${rect.left}px`;
          popup.style.top = `${rect.bottom + 4}px`;
        }
      };

      return {
        onStart: (props: any) => {
          currentItems = props.items;
          currentCommand = props.command;
          selectedIndex = 0;
          popup = document.createElement('div');
          popup.style.cssText = 'position:fixed;z-index:9999;background:#fff;border:1px solid #d1d5db;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.15);max-height:240px;overflow-y:auto;min-width:220px;';
          document.body.appendChild(popup);
          renderList();
          position(props.clientRect);
        },
        onUpdate: (props: any) => {
          currentItems = props.items;
          currentCommand = props.command;
          selectedIndex = 0;
          renderList();
          position(props.clientRect);
        },
        onKeyDown: (props: any) => {
          if (!currentItems.length) return props.event.key === 'Escape';
          if (props.event.key === 'ArrowDown') {
            selectedIndex = (selectedIndex + 1) % currentItems.length;
            renderList();
            return true;
          }
          if (props.event.key === 'ArrowUp') {
            selectedIndex = (selectedIndex - 1 + currentItems.length) % currentItems.length;
            renderList();
            return true;
          }
          if (props.event.key === 'Enter' || props.event.key === 'Tab') {
            currentCommand?.(currentItems[selectedIndex]);
            return true;
          }
          if (props.event.key === 'Escape') {
            return true;
          }
          return false;
        },
        onExit: () => {
          popup?.remove();
          popup = null;
        },
      };
    },
  };
}

// Custom extensions for font-family and font-size
const FontFamily = Extension.create({
  name: 'fontFamily',
  addOptions() { return { types: ['textStyle'] }; },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontFamily: {
            default: null,
            parseHTML: (element) => element.style.fontFamily || null,
            renderHTML: (attributes) => {
              if (!attributes.fontFamily) return {};
              return { style: `font-family: ${attributes.fontFamily}` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setFontFamily: (fontFamily: string) => ({ commands }) => {
        return commands.setMark('textStyle', { fontFamily });
      },
      unsetFontFamily: () => ({ commands }) => {
        return commands.resetAttributes('textStyle', 'fontFamily');
      },
    } as any;
  },
});

const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() { return { types: ['textStyle'] }; },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize || null,
            renderHTML: (attributes) => {
              if (!attributes.fontSize) return {};
              return { style: `font-size: ${attributes.fontSize}` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setFontSize: (fontSize: string) => ({ commands }) => {
        return commands.setMark('textStyle', { fontSize });
      },
      unsetFontSize: () => ({ commands }) => {
        return commands.resetAttributes('textStyle', 'fontSize');
      },
    } as any;
  },
});

const Highlight = Extension.create({
  name: 'highlight',
  addOptions() { return { types: ['textStyle'] }; },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          highlight: {
            default: null,
            parseHTML: (element) => element.style.backgroundColor || null,
            renderHTML: (attributes) => {
              if (!attributes.highlight) return {};
              return { style: `background-color: ${attributes.highlight}` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setHighlight: (color: string) => ({ commands }) => {
        return commands.setMark('textStyle', { highlight: color });
      },
      unsetHighlight: () => ({ commands }) => {
        return commands.resetAttributes('textStyle', 'highlight');
      },
    } as any;
  },
});

const SuperscriptExtension = Extension.create({
  name: 'superscript',
  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          superscript: {
            default: false,
            parseHTML: (element) => element.style.verticalAlign === 'super',
            renderHTML: (attributes) => {
              if (!attributes.superscript) return {};
              return { style: 'vertical-align: super; font-size: 0.8em' };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      toggleSuperscript: () => ({ commands }) => {
        return commands.toggleMark('textStyle', { superscript: true });
      },
    } as any;
  },
});

const SubscriptExtension = Extension.create({
  name: 'subscript',
  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          subscript: {
            default: false,
            parseHTML: (element) => element.style.verticalAlign === 'sub',
            renderHTML: (attributes) => {
              if (!attributes.subscript) return {};
              return { style: 'vertical-align: sub; font-size: 0.8em' };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      toggleSubscript: () => ({ commands }) => {
        return commands.toggleMark('textStyle', { subscript: true });
      },
    } as any;
  },
});

// Los correos de producción son HTML con estilos inline (tablas de detalle,
// párrafos con color/tamaño puntual) — TipTap por defecto NO conserva
// atributos que no estén declarados explícitamente en el esquema de cada
// nodo, así que sin esto, abrir un correo por defecto en modo Diseño y
// guardar sin tocar nada perdería silenciosamente el `style`/`width`/etc.
// original de las tablas y bloques.
const PreserveEmailAttrs = Extension.create({
  name: 'preserveEmailAttrs',
  addGlobalAttributes() {
    return [
      {
        types: ['paragraph', 'heading', 'table', 'tableRow', 'tableCell', 'tableHeader', 'image', 'bulletList', 'orderedList', 'listItem', 'blockquote'],
        attributes: {
          style: {
            default: null,
            parseHTML: (element: HTMLElement) => element.getAttribute('style') || null,
            renderHTML: (attributes: any) => (attributes.style ? { style: attributes.style } : {}),
          },
        },
      },
      {
        types: ['table'],
        attributes: {
          role: {
            default: null,
            parseHTML: (element: HTMLElement) => element.getAttribute('role') || null,
            renderHTML: (attributes: any) => (attributes.role ? { role: attributes.role } : {}),
          },
          width: {
            default: null,
            parseHTML: (element: HTMLElement) => element.getAttribute('width') || null,
            renderHTML: (attributes: any) => (attributes.width ? { width: attributes.width } : {}),
          },
          cellpadding: {
            default: null,
            parseHTML: (element: HTMLElement) => element.getAttribute('cellpadding') || null,
            renderHTML: (attributes: any) => (attributes.cellpadding ? { cellpadding: attributes.cellpadding } : {}),
          },
          cellspacing: {
            default: null,
            parseHTML: (element: HTMLElement) => element.getAttribute('cellspacing') || null,
            renderHTML: (attributes: any) => (attributes.cellspacing ? { cellspacing: attributes.cellspacing } : {}),
          },
        },
      },
    ];
  },
});

interface Props {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: string;
  variables?: EmailVariable[];
}

// ── small toolbar button ──────────────────────────────────────────────────────
const Btn: React.FC<{
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}> = ({ onClick, active, disabled, title, children }) => (
  <button
    type="button"
    title={title}
    disabled={disabled}
    onClick={onClick}
    className={`p-1.5 rounded text-sm transition-colors
      ${active ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}
      ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
  >
    {children}
  </button>
);

const Sep = () => <div className="w-px h-5 bg-gray-200 mx-0.5 self-center" />;

// ── main component ────────────────────────────────────────────────────────────
const RichTextEditor: React.FC<Props> = ({
  value,
  onChange,
  placeholder = 'Escribe el contenido del correo...',
  minHeight = '180px',
  variables = [],
}) => {
  const [mode, setMode] = useState<'visual' | 'html'>('visual');
  const [htmlDraft, setHtmlDraft] = useState(value);
  const lastValueRef = useRef(value);
  const variablesRef = useRef(variables);
  useEffect(() => { variablesRef.current = variables; }, [variables]);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      TextStyle,
      Color,
      FontFamily,
      FontSize,
      Highlight,
      SuperscriptExtension,
      SubscriptExtension,
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      Image.configure({ inline: false, allowBase64: true }),
      Mention.configure({
        suggestion: createVariableSuggestion(variablesRef),
        renderHTML: ({ node }) => ['span', { class: 'email-var-mention' }, `{{${node.attrs.id}}}`],
        renderText: ({ node }) => `{{${node.attrs.id}}}`,
      }),
      PreserveEmailAttrs,
    ],
    content: value,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      lastValueRef.current = html;
      onChange(html);
    },
  });

  // Sync when value changes externally (e.g. switching email event type)
  useEffect(() => {
    if (value !== lastValueRef.current) {
      lastValueRef.current = value;
      setHtmlDraft(value);
      if (editor) {
        // Siempre actualizar el editor, sin importar el modo
        editor.commands.setContent(value || '', { emitUpdate: false });
      }
    }
  }, [value, editor]);

  const switchToHtml = useCallback(() => {
    if (editor) setHtmlDraft(editor.getHTML());
    setMode('html');
  }, [editor]);

  const switchToVisual = useCallback(() => {
    if (editor) {
      editor.commands.setContent(htmlDraft, { emitUpdate: false });
      lastValueRef.current = htmlDraft;
    }
    onChange(htmlDraft);
    setMode('visual');
  }, [editor, htmlDraft, onChange]);

  const handleHtmlChange = (v: string) => {
    setHtmlDraft(v);
    onChange(v);
  };

  // Solo para el modo HTML (textarea plano, sin ProseMirror detrás). En modo
  // visual NO se maneja aquí a propósito: ProseMirror ya trae su propio
  // handler nativo de drop (editHandlers.drop en prosemirror-view/input.ts)
  // que inserta el texto exactamente en el punto donde se soltó — duplicar
  // esa inserción aquí (como hacía antes) dejaba la variable pegada dos
  // veces, porque ProseMirror no detiene la propagación del evento.
  const handleDrop = (e: React.DragEvent) => {
    if (mode !== 'html') return;
    e.preventDefault();
    e.stopPropagation();

    const variable = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('application/x-email-variable');
    if (variable) {
      const textarea = e.currentTarget.querySelector('textarea') as HTMLTextAreaElement;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newHtml = htmlDraft.substring(0, start) + variable + htmlDraft.substring(end);
        handleHtmlChange(newHtml);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + variable.length;
          textarea.focus();
        }, 0);
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const setLink = useCallback(() => {
    if (!editor) return;
    const prev = editor.getAttributes('link').href ?? '';
    const url = window.prompt('URL del enlace', prev);
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
    }
  }, [editor]);

  const insertImage = useCallback(() => {
    if (!editor) return;
    const url = window.prompt('URL de la imagen (ej. {{logo_url}} o una URL pública)');
    if (!url) return;
    editor.chain().focus().setImage({ src: url }).run();
  }, [editor]);

  const insertTable = useCallback(() => {
    if (!editor) return;
    editor.chain().focus().insertTable({ rows: 3, cols: 2, withHeaderRow: false }).run();
  }, [editor]);

  const htmlLineCount = htmlDraft.split('\n').length;

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-400 focus-within:border-blue-400">

      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-0.5 flex-wrap px-2 py-1.5 bg-gray-50 border-b border-gray-200">

        {/* Mode toggle */}
        <div className="flex rounded overflow-hidden border border-gray-300 mr-1">
          <button
            type="button"
            onClick={switchToVisual}
            className={`px-2.5 py-1 text-xs font-medium transition-colors ${
              mode === 'visual' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            Diseño
          </button>
          <button
            type="button"
            onClick={switchToHtml}
            className={`px-2.5 py-1 text-xs font-medium transition-colors border-l border-gray-300 ${
              mode === 'html' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            HTML
          </button>
        </div>

        {mode === 'visual' && editor && (
          <>
            <Sep />

            {/* Undo / Redo */}
            <Btn title="Deshacer (Ctrl+Z)" disabled={!editor.can().undo()} onClick={() => editor.chain().focus().undo().run()}>
              <Undo2 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Rehacer (Ctrl+Y)" disabled={!editor.can().redo()} onClick={() => editor.chain().focus().redo().run()}>
              <Redo2 className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Font family selector */}
            <select
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) {
                  (editor.chain().focus() as any).setFontFamily(e.target.value).run();
                } else {
                  (editor.chain().focus() as any).unsetFontFamily().run();
                }
                e.target.value = '';
              }}
              className="px-2 py-1 text-xs border border-gray-300 rounded hover:border-gray-400 transition-colors cursor-pointer"
              title="Tipo de fuente"
            >
              <option value="">Fuente</option>
              <option value="Arial, sans-serif">Arial</option>
              <option value="'Courier New', monospace">Courier</option>
              <option value="Georgia, serif">Georgia</option>
              <option value="Verdana, sans-serif">Verdana</option>
              <option value="'Times New Roman', serif">Times</option>
              <option value="'Trebuchet MS', sans-serif">Trebuchet</option>
            </select>

            {/* Font size selector */}
            <select
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) {
                  (editor.chain().focus() as any).setFontSize(e.target.value).run();
                } else {
                  (editor.chain().focus() as any).unsetFontSize().run();
                }
                e.target.value = '';
              }}
              className="px-2 py-1 text-xs border border-gray-300 rounded hover:border-gray-400 transition-colors cursor-pointer"
              title="Tamaño de fuente"
            >
              <option value="">Tamaño</option>
              <option value="12px">12px</option>
              <option value="14px">14px</option>
              <option value="16px">16px</option>
              <option value="18px">18px</option>
              <option value="20px">20px</option>
              <option value="24px">24px</option>
              <option value="28px">28px</option>
              <option value="32px">32px</option>
            </select>

            <Sep />

            {/* Text style */}
            <Btn title="Negrita (Ctrl+B)" active={editor.isActive('bold')} onClick={() => editor.chain().focus().toggleBold().run()}>
              <Bold className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Cursiva (Ctrl+I)" active={editor.isActive('italic')} onClick={() => editor.chain().focus().toggleItalic().run()}>
              <Italic className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Subrayado (Ctrl+U)" active={editor.isActive('underline')} onClick={() => editor.chain().focus().toggleUnderline().run()}>
              <UnderlineIcon className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Tachado" active={editor.isActive('strike')} onClick={() => editor.chain().focus().toggleStrike().run()}>
              <Strikethrough className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Headings */}
            <Btn title="Título 1" active={editor.isActive('heading', { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}>
              <Heading1 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Título 2" active={editor.isActive('heading', { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
              <Heading2 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Párrafo normal" active={editor.isActive('paragraph')} onClick={() => editor.chain().focus().setParagraph().run()}>
              <Type className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Alignment */}
            <Btn title="Alinear izquierda" active={editor.isActive({ textAlign: 'left' })} onClick={() => editor.chain().focus().setTextAlign('left').run()}>
              <AlignLeft className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Centrar" active={editor.isActive({ textAlign: 'center' })} onClick={() => editor.chain().focus().setTextAlign('center').run()}>
              <AlignCenter className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Alinear derecha" active={editor.isActive({ textAlign: 'right' })} onClick={() => editor.chain().focus().setTextAlign('right').run()}>
              <AlignRight className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Lists */}
            <Btn title="Lista con viñetas" active={editor.isActive('bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()}>
              <List className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Lista numerada" active={editor.isActive('orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
              <ListOrdered className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Link */}
            <Btn title="Insertar enlace" active={editor.isActive('link')} onClick={setLink}>
              <Link2 className="w-3.5 h-3.5" />
            </Btn>
            {editor.isActive('link') && (
              <Btn title="Quitar enlace" onClick={() => editor.chain().focus().unsetLink().run()}>
                <Link2Off className="w-3.5 h-3.5" />
              </Btn>
            )}

            <Sep />

            {/* Table & Image */}
            <Btn title="Insertar tabla" active={editor.isActive('table')} onClick={insertTable}>
              <Table2 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Insertar imagen (URL)" onClick={insertImage}>
              <ImagePlus className="w-3.5 h-3.5" />
            </Btn>
            {editor.isActive('table') && (
              <>
                <Btn title="Agregar fila" onClick={() => editor.chain().focus().addRowAfter().run()}>
                  <Rows3 className="w-3.5 h-3.5" />
                </Btn>
                <Btn title="Agregar columna" onClick={() => editor.chain().focus().addColumnAfter().run()}>
                  <Columns3 className="w-3.5 h-3.5" />
                </Btn>
                <Btn title="Eliminar fila" onClick={() => editor.chain().focus().deleteRow().run()}>
                  <Rows3 className="w-3.5 h-3.5 opacity-50" />
                </Btn>
                <Btn title="Eliminar columna" onClick={() => editor.chain().focus().deleteColumn().run()}>
                  <Columns3 className="w-3.5 h-3.5 opacity-50" />
                </Btn>
                <Btn title="Eliminar tabla" onClick={() => editor.chain().focus().deleteTable().run()}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Btn>
              </>
            )}

            <Sep />

            {/* Blockquote & Code */}
            <Btn title="Cita (Blockquote)" active={editor.isActive('blockquote')} onClick={() => editor.chain().focus().toggleBlockquote().run()}>
              <Quote className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Código" active={editor.isActive('codeBlock')} onClick={() => editor.chain().focus().toggleCodeBlock().run()}>
              <Code className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Divider / rule */}
            <Btn title="Línea horizontal" onClick={() => editor.chain().focus().setHorizontalRule().run()}>
              <Minus className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Superscript & Subscript */}
            <Btn title="Superíndice" active={editor.isActive('textStyle', { superscript: true })} onClick={() => (editor.chain().focus() as any).toggleSuperscript().run()}>
              <Superscript className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Subíndice" active={editor.isActive('textStyle', { subscript: true })} onClick={() => (editor.chain().focus() as any).toggleSubscript().run()}>
              <Subscript className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Text color & Highlight */}
            <div className="flex items-center gap-1 pl-0.5" title="Color del texto">
              <span className="text-xs text-gray-500 font-bold">A</span>
              <input
                type="color"
                defaultValue="#000000"
                onChange={e => editor.chain().focus().setColor(e.target.value).run()}
                className="w-5 h-5 rounded cursor-pointer border border-gray-300 p-0"
                title="Color del texto"
              />
            </div>

            <div className="flex items-center gap-1 pl-0.5" title="Color de fondo (Highlight)">
              <Highlighter className="w-3.5 h-3.5 text-gray-500" />
              <input
                type="color"
                defaultValue="#FFFF00"
                onChange={e => (editor.chain().focus() as any).setHighlight(e.target.value).run()}
                className="w-5 h-5 rounded cursor-pointer border border-gray-300 p-0"
                title="Fondo"
              />
            </div>

            <Sep />

            {/* Clear formatting */}
            <Btn title="Limpiar formato" onClick={() => editor.chain().focus().clearNodes().run()}>
              <RotateCcw className="w-3.5 h-3.5" />
            </Btn>
          </>
        )}

        {/* HTML mode info badge */}
        {mode === 'html' && (
          <div className="flex items-center gap-1.5 ml-1">
            <Code2 className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs text-gray-400 font-mono">código fuente</span>
            <span className="text-xs text-gray-300 ml-1">
              {htmlLineCount} {htmlLineCount === 1 ? 'línea' : 'líneas'}
            </span>
          </div>
        )}
      </div>

      {/* ── Editor area ──────────────────────────────────────────────────── */}
      {mode === 'visual' ? (
        <div
          className="px-3 py-2 text-sm transition-colors hover:bg-gray-50"
          style={{ minHeight, maxHeight: '340px', overflowY: 'auto' }}
          onClick={() => editor?.commands.focus()}
        >
          <EditorContent editor={editor} className="outline-none" />
        </div>
      ) : (
        <div className="relative bg-gray-950" onDrop={handleDrop} onDragOver={handleDragOver}>
          <textarea
            value={htmlDraft}
            onChange={e => handleHtmlChange(e.target.value)}
            spellCheck={false}
            autoComplete="off"
            className="w-full px-3 py-2 text-xs font-mono bg-transparent text-green-300 resize-y focus:outline-none leading-relaxed"
            style={{ minHeight, maxHeight: '340px' }}
            placeholder="<!-- Escribe HTML aquí... -->"
          />
        </div>
      )}

      {/* ── CSS for TipTap visual editor ─────────────────────────────────── */}
      <style>{`
        .tiptap, .ProseMirror { outline: none; min-height: ${minHeight}; }
        .tiptap p, .ProseMirror p { margin: 0.3rem 0; line-height: 1.5; }
        .tiptap h1, .ProseMirror h1 { font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0; }
        .tiptap h2, .ProseMirror h2 { font-size: 1.25rem; font-weight: 600; margin: 0.5rem 0; }
        .tiptap h3, .ProseMirror h3 { font-size: 1.1rem; font-weight: 600; margin: 0.4rem 0; }
        .tiptap ul, .ProseMirror ul { list-style-type: disc; padding-left: 1.2rem; margin: 0.3rem 0; }
        .tiptap ol, .ProseMirror ol { list-style-type: decimal; padding-left: 1.2rem; margin: 0.3rem 0; }
        .tiptap a, .ProseMirror a { color: #4272A5; text-decoration: underline; }
        .tiptap hr, .ProseMirror hr { border: none; border-top: 1px solid #e5e7eb; margin: 0.75rem 0; }
        .tiptap strong, .ProseMirror strong { font-weight: 700; }
        .tiptap em, .ProseMirror em { font-style: italic; }
        .tiptap s, .ProseMirror s { text-decoration: line-through; }
        .tiptap u, .ProseMirror u { text-decoration: underline; }
        .tiptap p.is-editor-empty:first-child::before,
        .ProseMirror p.is-editor-empty:first-child::before {
          color: #9ca3af;
          content: attr(data-placeholder);
          float: left;
          height: 0;
          pointer-events: none;
        }
        .tiptap img, .ProseMirror img { max-width: 100%; height: auto; }
        .tiptap img.ProseMirror-selectednode, .ProseMirror img.ProseMirror-selectednode {
          outline: 2px solid #4272A5;
        }
        .tiptap table, .ProseMirror table {
          border-collapse: collapse;
          table-layout: fixed;
          width: 100%;
          margin: 0.5rem 0;
          overflow: hidden;
        }
        .tiptap td, .tiptap th, .ProseMirror td, .ProseMirror th {
          border: 1px solid #e5e5ea;
          padding: 8px 10px;
          vertical-align: top;
          position: relative;
        }
        .tiptap th, .ProseMirror th {
          background-color: #f5f5f7;
          font-weight: 600;
          text-align: left;
        }
        .tiptap .selectedCell, .ProseMirror .selectedCell {
          background-color: rgba(66, 114, 165, 0.12);
        }
        .tiptap .column-resize-handle, .ProseMirror .column-resize-handle {
          background-color: #4272A5;
          bottom: -2px;
          position: absolute;
          right: -2px;
          top: 0;
          width: 3px;
          pointer-events: none;
        }
        .tiptap .email-var-mention, .ProseMirror .email-var-mention {
          background-color: #eff6ff;
          color: #1d4ed8;
          border: 1px solid #bfdbfe;
          border-radius: 4px;
          padding: 0 3px;
          font-family: monospace;
          font-size: 0.85em;
        }
      `}</style>
    </div>
  );
};

export default RichTextEditor;
