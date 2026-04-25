import { Link } from 'react-router-dom';

function NotFoundPage() {
  return (
    <main className="not-found-wrap">
      <section className="not-found-card">
        <h1 className="not-found-title">Page not found</h1>
        <p className="not-found-subtitle">
          The route does not exist in this GeoSeer workspace.
        </p>
        <Link className="not-found-button" to="/dashboard">
          Go to dashboard
        </Link>
      </section>
    </main>
  );
}

export default NotFoundPage;
