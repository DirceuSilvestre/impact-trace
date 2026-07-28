from typing import List, Optional, Set
import networkx as nx
from rich.console import Console
from rich.tree import Tree

console = Console()


def build_impact_tree(
    graph: nx.DiGraph,
    changed_files: List[str],
    unaffected_files: Optional[List[str]] = None,
    show_unaffected: bool = False,
) -> Tree:
    """
    Constrói uma estrutura de árvore hierárquica usando a biblioteca Rich
    demonstrando a propagação de impacto a partir dos arquivos alterados
    até os módulos consumidores.

    Args:
        graph (nx.DiGraph): O grafo de dependências do projeto.
        changed_files (List[str]): Arquivos alterados no Git (Causa Raiz).
        unaffected_files (Optional[List[str]]): Arquivos sem impacto.
        show_unaffected (bool): Se True, inclui o ramo de arquivos seguros.

    Returns:
        Tree: Objeto Tree da biblioteca Rich formatado para exibição.
    """
    root_tree = Tree(
        "[bold cyan]🌳 Árvore de Propagação de Impacto (ImpactTrace)[/bold cyan]",
        guide_style="dim cyan",
    )

    if not changed_files:
        root_tree.add("[bold yellow]ℹ Nenhum arquivo alterado detectado.[/bold yellow]")
        return root_tree

    # Ramo principal: Causa Raiz
    changed_branch = root_tree.add(
        "[bold yellow]📝 Arquivos Modificados no Git (Origem)[/bold yellow]"
    )

    for changed in changed_files:
        changed_node = changed_branch.add(f"[bold yellow]{changed}[/bold yellow]")

        if not graph.has_node(changed):
            changed_node.add(
                "[dim italic](Arquivo novo ou sem conexões no grafo)[/dim italic]"
            )
            continue

        # Recursão para montar a árvore de dependentes
        _add_dependents_recursively(
            graph,
            parent_tree_node=changed_node,
            current_node=changed,
            visited={changed},
            depth=1,
        )

    # Ramo secundário opcional: Arquivos Seguros
    if show_unaffected and unaffected_files:
        unaffected_branch = root_tree.add(
            f"[bold green]🛡️ Arquivos Íntegros e Seguros ({len(unaffected_files)})[/bold green]"
        )
        for safe_file in unaffected_files:
            unaffected_branch.add(f"[bold green]{safe_file}[/bold green]")

    return root_tree


def _add_dependents_recursively(
    graph: nx.DiGraph,
    parent_tree_node: Tree,
    current_node: str,
    visited: Set[str],
    depth: int,
) -> None:
    """
    Função auxiliar recursiva que percorre os predecessores do nó no grafo
    (módulos que importam o nó atual) construindo os galhos da árvore.
    """
    # Predecessores = arquivos que importam o current_node
    dependents = sorted(list(graph.predecessors(current_node)))

    if not dependents:
        if depth == 1:
            parent_tree_node.add(
                "[dim green]✓ Nenhuma dependência afetada (Mudança isolada)[/dim green]"
            )
        return

    for dep in dependents:
        if dep in visited:
            # Previne estouro de pilha/loops em dependências circulares
            parent_tree_node.add(f"[dim red]🔄 {dep} (Ciclo de importação detectado)[/dim red]")
            continue

        new_visited = visited.copy()
        new_visited.add(dep)

        if depth == 1:
            # Impacto Direto -> Vermelho
            label = f"[bold red]💥 {dep}[/bold red] [dim italic](Impacto Direto)[/dim italic]"
            child_node = parent_tree_node.add(label)
        else:
            # Impacto Indireto -> Magenta
            label = f"[bold magenta]⚠️ {dep}[/bold magenta] [dim italic](Impacto Indireto - Nível {depth})[/dim italic]"
            child_node = parent_tree_node.add(label)

        # Propaga a busca para os próximos níveis da cascata
        _add_dependents_recursively(
            graph,
            parent_tree_node=child_node,
            current_node=dep,
            visited=new_visited,
            depth=depth + 1,
        )


def render_impact_tree(
    graph: nx.DiGraph,
    changed_files: List[str],
    unaffected_files: Optional[List[str]] = None,
    show_unaffected: bool = False,
) -> None:
    """
    Helper direto para construir e renderizar a árvore no terminal.
    """
    tree = build_impact_tree(graph, changed_files, unaffected_files, show_unaffected)
    console.print()
    console.print(tree)
    console.print()