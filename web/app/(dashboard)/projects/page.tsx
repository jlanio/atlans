import ProjectActions from '../../components/projects';

// Sem provider: a lista vive no hook de dados de Projetos (`use-projetos-dados`),
// e os diálogos recebem o workflow por prop.
export default function WorkflowsPage() {
  return <ProjectActions />;
}
