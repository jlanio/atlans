import ProjectActions from '../../components/projects';

// No provider: the list lives in the Projects data hook (`use-projetos-dados`),
// and the dialogs receive the workflow by prop.
export default function WorkflowsPage() {
  return <ProjectActions />;
}
